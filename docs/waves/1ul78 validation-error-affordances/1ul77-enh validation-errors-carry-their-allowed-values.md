# Validation Errors Carry Their Allowed Values

Change ID: `1ul77-enh validation-errors-carry-their-allowed-values`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-08-06
Wave: 1ul78 validation-error-affordances

## Rationale

Field observation from a downstream project: an agent hit three `wf_validate_docs` errors on a wave record, including ``invalid `Change Status` declaration `Change Status: `implemented — awaiting delivery review` ``. The error named the offending value but not the accepted ones, so the agent spent two searches and two shell commands discovering that `Change Status` is an enum, then needed a second correction from the operator to learn that `review` is not reachable from `planned` and `active` was the right token.

Every fact the agent had to discover is already a constant in this repository. `ALLOWED_CHANGE_STATUS_TRANSITIONS` holds both the full value set and the per-status reachable set. Withholding it converts a one-line fix into an exploration loop, and the exploration can still land on a value that is valid in shape but unreachable from the current status.

A census of the lint surface shows this is systemic rather than a `Change Status` quirk. Across nine validator modules there are 198 `failures.append` sites. Exactly **three** name their allowed values, and all three are in the memory validators:

- `wave_validators.py:1331` ``unknown memory kind {...!r}; allowed: {', '.join(MEMORY_KINDS)}``
- `wave_validators.py:1339` ``missing `Status:` line (one of {', '.join(MEMORY_STATUSES)})``
- `wave_validators.py:1343` ``memory `Status` must be one of {', '.join(MEMORY_STATUSES)}``

That is decisive for the design: the convention this change wants already exists in this file, is already derived from the constant at runtime, and is already proven in production. The status family simply never adopted it. This is therefore an extension of a house pattern, not a new mechanism, which is why the risk is low and why no new abstraction is warranted.

The transition site makes the gap concrete. At `wave_validators.py:1204-1212` the validator computes `allowed_previous` at line 1207, tests membership at 1208, and then reports only ``invalid status progression `planned` -> `review` `` without printing the set it just computed and still holds in scope. The exact answer the operator had to supply by hand is a local variable at the point of failure.

A second, subtler defect compounds it. `CHANGE_STATUS_PATTERN` validates only shape (`[a-z0-9-]+`), so a wrong-but-well-formed token such as `implemented` passes the shape check and fails later at membership or transition. The value set therefore has to reach the caller from more than one error path, not just the one that fired in the field report.

## Requirements

1. Every docs-lint failure whose validity is defined by a fixed value set must state that set in the error message.
2. The stated set must be derived at runtime from the same constant the validator checks against. No hand-authored duplicate lists.
3. Where validity depends on the current value rather than being global (status transitions), the message must state the values reachable **from that current value**, and identify the current value it is reasoning from.
4. Stating a value set is authoritative guidance, not a new gate. This change must introduce no membership check, and nothing that lints clean today may newly fail. Where a field already has more than one failure path, each existing path carries the set.
5. Message formatting must be one shared helper, so a new enum-backed validator inherits the behavior instead of reimplementing it. The helper must reconcile the two phrasings already in the tree (``; allowed: <values>`` at line 1331 and ``must be one of <values>`` at line 1343) into a single form and adopt the existing memory messages onto it, rather than introducing a third phrasing alongside them.
6. Existing error text that callers or tests match on must keep its leading `ERROR: <path>: <existing message>` prefix and its existing wording. The allowed-value text is appended, not substituted.

## Scope

**Problem statement:** Validation errors report what is wrong without reporting what would be right, forcing every caller to rediscover value sets that already exist as constants.

**In scope:**

- A shared allowed-values formatter in `wave_lint_lib`.
- Applying it to the enum-backed failure sites in `wave_validators.py`: change status, item status, previous status, memory kind, memory status, and the transition validators.
- The shape-check paths for the same fields, so both routes carry the set.
- Regression coverage asserting that each affected message names its values and that the named values are read from the constant.

**Out of scope:**

- The 177 failure sites with no fixed value set (path existence, required sections, link targets, secrets). They have no list to offer.
- Changing any value set, transition table, or what counts as valid. This change is message-only, adds no membership check, and must not cause any currently-clean document to fail.
- Reconciling the `Change Status` declaration vocabulary. Readiness established that `implemented` is the dominant real value (1000 uses) and belongs to no constant; whether it joins the canonical set is a separate decision recorded in the Decision Log.
- The MCP envelope schema. Messages flow into `diagnostics[].message` unchanged; no new envelope field.
- Design-system, secrets, and docs-constants validators, unless a shared helper reaches them without added risk.

## Acceptance Criteria

- [x] AC-1: A `Change Status` value that fails the shape check produces an error naming the full accepted value set, read from `ALLOWED_CHANGE_STATUS_TRANSITIONS`.
- [x] AC-2: No declaration that lints clean before this change fails after it. Specifically, `Change Status: `implemented`` (1000 occurrences, absent from the transition table) still lints clean, proving the value set is published as guidance without becoming a gate.
- [x] AC-3: A rejected status transition produces an error naming the current status and the values reachable from it, and that reachable set matches the constant for that status.
- [x] AC-4: A mutation test proves the messages are constant-derived: adding a value to the transition table changes the emitted message with no test-fixture edit.
- [x] AC-5: The three memory messages that already enumerate their sets are migrated onto the shared helper with their information content preserved, proving the helper generalizes and leaving exactly one phrasing in the tree.
- [x] AC-6: Every affected message retains its existing `ERROR: <path>: <original wording>` prefix, verified against the current strings.
- [x] AC-7: The full framework suite and docs-lint pass.

## Tasks

- [x] Enumerate the enum-backed failure sites and record the constant each one checks against.
- [x] Add the shared formatter to `wave_lint_lib` with a single output shape.
- [x] Apply it to the change/item status shape-check sites.
- [x] Apply it to the membership and transition sites, including the reachable-from-current wording.
- [x] Apply it to the memory kind and memory status sites.
- [x] Add regression tests per AC-1 through AC-3, AC-5, and AC-6.
- [x] Add the AC-4 mutation test that varies the constant rather than the fixture.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream          | Owner       | Depends On | Notes                                                        |
| ------------------- | ----------- | ---------- | ------------------------------------------------------------ |
| formatter           | implementer | none       | Shared helper and its output shape                            |
| status-sites        | implementer | formatter  | Shape, membership, and transition paths                       |
| memory-sites        | implementer | formatter  | Kind and status                                               |
| coverage            | implementer | status-sites, memory-sites | Includes the constant-derived mutation test    |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`

List real repository-relative paths here. Prepare uses these paths—not Scope, Rationale, or other narrative—to select automatic review lanes. Path scoring is a floor, not a ceiling: ANY lane may also be requested by judgment through the wave's `Requested review lanes` field, and the coordinator is expected to use it. Architecture review especially is usually a judgment call, since an ownership shift or a protocol change can live entirely in files whose paths recruit only the code lane. A requested lane is always honored and costs no receipt churn.

## Affected Architecture Docs

`N/A`. The change is confined to message construction inside the lint validators. It moves no boundary, alters no control flow, and changes no verification outcome: the same inputs pass and fail exactly as before.

## AC Priority


| AC   | Priority       | Rationale                                                                                   |
| ---- | -------------- | ------------------------------------------------------------------------------------------- |
| AC-1 | required       | The shape path is the one that fired in the field report.                                     |
| AC-2 | required       | The membership path is how a plausible-but-wrong token such as `implemented` actually fails.  |
| AC-3 | required       | Reachability was the second correction the operator had to supply by hand.                    |
| AC-4 | required       | Without it the lists are duplicates that will drift, which is worse than no list.             |
| AC-5 | important      | Proves the helper generalizes past status, which is the stated intent.                        |
| AC-6 | required       | Callers and tests match on the existing prefix; changing it would be a silent contract break. |
| AC-7 | required       | Standard gate.                                                                                |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-06 | Implemented the shared `allowed_values_suffix` helper and wired it into the four status shape sites, the transition site, and the three memory sites | `wave_lint_lib/constants.py`; `wave_validators.py:20,1184-1196,1209-1214,1333-1350` |
| 2026-08-06 | AC-4's anti-drift test proven non-vacuous by mutation: replacing the derived list with a hand-written one kills it | Baseline OK; mutant `FAILED (failures=1)` on ``'`teleported`' not found``. The mutant also printed the GLOBAL set for terminal status `complete`, which is the exact drift the test guards |
| 2026-08-06 | Requirement 6 and AC-5 boundary: Requirement 6 governs sites where text is APPENDED; AC-5 authorizes rewording the three memory messages onto the one helper phrasing. One assertion was updated accordingly | `test_docs_lint.py:3456` changed from ``memory `Status` must be one of`` to ``memory `Status` is invalid (got 'maybe')`` |
| 2026-08-06 | Regression found and fixed OUTSIDE this change: an earlier README/install-block dedup pass dropped two phrases required by the bridge-carrier contract test | `test_upgrade_protocol.py` `test_public_bridge_carriers_assign_agent_shell_and_multihost_restart` requires `ordinary non-MCP shell`, `operator does not copy or type`, and `restart every attached host`; both carriers now pass |
| 2026-08-06 | Full suite 6883/62 OK, docs-lint ok. One `test_server_tools` failure in an intermediate run did not reproduce standalone (1584 OK) or on re-run | `run_tests.py` |
| 2026-08-06 | Delivery review finding 1, REPAIRED: the blocked-dependency message never printed `terminal_statuses`, though it is bound at the check. Same defect shape as the transition site, missed because implementation followed the sites the plan named instead of auditing every enum-governed failure | `wave_validators.py:1226-1233`; `test_blocked_dependency_names_which_statuses_would_unblock_it` |
| 2026-08-06 | Delivery review finding 2, REPAIRED: the watchpoints message hand-listed 3 of 6 markers (`retry`, `defer`, `move` omitted). This was hand-written drift of exactly the kind this change exists to remove, inside the file being changed | `WAVE_WATCHPOINT_MARKERS` has 6 entries; `wave_validators.py:1242-1246`; `test_watchpoint_marker_message_lists_every_marker_that_satisfies_it` |
| 2026-08-06 | Delivery review finding 3, REPAIRED: the AC-2 test asserted `"; allowed:"` never appears, which passed only because the transition message renders `"; allowed from \`x\`:"`. It never proved its stated claim and broke as soon as a second message legitimately used the plain form. Narrowed to the claim actually made, with the pre-existing transition and dependency failures explained rather than asserted away | `test_publishing_the_vocabulary_did_not_turn_it_into_a_gate`; AC-2 baseline already covered by the pristine-fixture assertion at `test_docs_lint.py:69` |
| 2026-08-06 | Risk-table mitigation performed: widest rendered message measured at 207 characters for the 11-value set, comparable to existing lint lines | `invalid \`Change Status\` declaration ...; allowed: <11 values>` |
| 2026-08-06 | Noted, out of scope: `TERMINAL_CHANGE_STATUSES` contains `done`, which is absent from the transition-table keys, so the terminal and transition vocabularies disagree independently of the `implemented` divergence | `constants.py:253` vs `:255-267` |
| 2026-08-06 | Noted at close, out of scope: the close gate uses a FOURTH vocabulary, a hardcoded blocklist rather than a constant, which is why `implemented` closes waves despite belonging to no status constant | `server_impl.py:16787` `open_statuses = {"stub", "planned", "ready", "active"}` |
| 2026-08-06 | This change set `Change Status: `complete`` rather than the house-convention `implemented`, because `complete` is the only value satisfying all four vocabularies at once: reachable from `planned`, terminal, and non-open | `constants.py:253,255-267`; `server_impl.py:16787` |
| 2026-08-06 | **Gapfill:** implement-stage instrumented retrieval registered zero calls against five changed non-docs files. Part of that is correct by the posture's own definition, since the census needed custom aggregation over every `failures.append` and the mutation and suite probes are executed shell work. Part is not: the region reads at `wave_validators.py:1204-1232` and `:1325-1366` and the test-file inspections were plain `sed`/`grep` where `code_read` and `code_outline` were the right instruments, and MCP retrieval was used only during plan and readiness. Recording this as a genuine posture miss rather than a justified fallback | `wf_close_wave` `retrieval_posture_gap`: 0 calls / 5 changed files |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-06 | Derive the printed set from the checked constant at runtime | A hand-written list in the message would drift from the validator silently, restoring the original problem while appearing to fix it | Static strings per site; a generated docs table the error links to |
| 2026-08-06 | Append to existing messages rather than rewrite them | Tests and callers match on the current wording and the `ERROR: <path>:` prefix | Rewrite messages for clarity, accepted as a later change |
| 2026-08-06 | Scope to enum-backed sites only | The remaining sites have no fixed set to offer, so a blanket sweep would add churn without information | Sweep all 198 sites |
| 2026-08-06 | Extend the existing memory-validator convention instead of designing a new one | Readiness review found three messages already doing this correctly from the constant; adopting the proven in-repo pattern removes design risk and avoids a third phrasing | Invent a formatter without reference to the existing three |
| 2026-08-06 | Print the transition set from the `allowed_previous` variable already in scope | At `wave_validators.py:1207` the reachable set is computed immediately before the failure, so the fix is local and cannot drift from the check | Recompute the set inside the message builder |
| 2026-08-06 | Publish the canonical status vocabulary as authoritative guidance without enforcing it | Operator direction: a value set can be authoritative without forcing validation. Readiness proved `Change Status` has no membership check at all, so `implemented` (1000 uses, in no constant, validator, or seed) lints clean. Enforcing the 11-value transition table would fail roughly 1040 existing declarations and require a migration, while publishing it steers new work at zero blast radius | Add a membership check and migrate existing docs; or print nothing until the vocabulary is reconciled |
| 2026-08-06 | Treat the `implemented` divergence as a separate finding, not part of this change | The declaration vocabulary was never defined, so `implemented` filled the vacuum by convention. Deciding whether it joins the canonical set is a semantics question with its own blast radius and does not block publishing the set we have | Fold the reconciliation into this wave |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Printed lists drift from the constants they describe | AC-4 varies the constant, not the fixture, so a hand-written list fails the test |
| AC-4's mutation test passes vacuously by patching the wrong module | `wave_validators.py:20` binds the constants via `from .constants import (...)` at module load, so patching `constants.ALLOWED_CHANGE_STATUS_TRANSITIONS` leaves the bound name untouched and the assertion would hold for the wrong reason. The test must patch `wave_validators.ALLOWED_CHANGE_STATUS_TRANSITIONS`, and must first assert the unpatched message does NOT contain the injected value |
| Long value sets make messages unreadable | One shared formatter with a single output shape; review the rendered text for the widest set (11 values) before closing |
| Appending text breaks callers matching on exact messages | AC-6 pins the existing prefix and wording; census the test suite for exact-match assertions before editing |
| Transition messages state a global set where a reachable subset is meant | AC-3 asserts the reachable set for a specific current status, not the union |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
