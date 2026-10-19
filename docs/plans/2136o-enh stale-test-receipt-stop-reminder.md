# Remind at turn end when framework edits left the test receipt stale

Change ID: `2136o-enh stale-test-receipt-stop-reminder`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-10-18
Wave: TBD

## Rationale

The Claude Code best-practices guide suggests a Stop hook as a deterministic check at turn end. In this repository the check that matters is the framework test receipt: close refuses a stale one (`framework_test_receipt_not_proven`).

Today the agent learns the receipt is stale only at close dry-run, often after reviews have been recorded. The Stop hooks record the session (`session-capture.py`) and context use (`context-efficiency-project.py`); neither looks at the receipt.

A cheap staleness test already exists. `lifecycle_gates._framework_test_receipt_status` (`lifecycle_gates.py:419-504`) compares `run_tests._hash_inputs()` with the receipt. It took about 0.06 s warm on 607 files.

**Parked (plan review, 2026-10-18).** Three reasons:
- As designed, the reminder reaches nobody. Claude Code writes a Stop hook's exit-0 stdout to the debug log, not to the transcript or the model (Claude Code hooks docs). The only ways a Stop hook reaches Claude are blocking or `additionalContext`, and both continue the conversation.
- Mid-implementation the receipt is normally stale, so a reminder mostly states the obvious.
- Close already checks the receipt deterministically.

If this is ever revisited, it belongs on a surface the agent reads, such as the SessionStart hook or the close dry-run diagnostics, not Stop.

## Requirements

1. The Claude Stop hook `session-capture.py` adds one advisory line when all three hold:
   - the framework test runner is present (the framework source repository; consuming targets get `not_applicable` and print nothing);
   - `_framework_test_receipt_status` reports `stale`, `not_ok` or `missing`;
   - no reminder has yet been printed for the current receipt.
2. The reminder fires at most once per receipt. It records the receipt's `inputs_hash` (or `missing`) under `.wavefoundry/cache/`, and stays quiet until a new receipt is written.
3. Any error in the check is swallowed with no output. The hook keeps exiting 0, as today.
4. The line names the command: `python3 .wavefoundry/framework/scripts/run_tests.py`.
5. Behaviour is the same on Windows, macOS, Linux and WSL2: in-process hashing through existing code, plus one small cache file written with the existing helpers.

## Scope

**Problem statement:** a stale framework test receipt is discovered only at close.

**In scope:**

- `claude_stop_source` in `.wavefoundry/framework/scripts/render_platform_surfaces.py`, and the rendered hook.
- Tests for the once-per-receipt rule and the runner-absent no-op.

**Out of scope:**

- Running tests from a hook.
- Blocking the Stop event.
- Other hosts.

## Acceptance Criteria

- [ ] AC-1: In a scratch framework checkout with a stale receipt, the first Stop run prints the reminder and the second prints nothing. After a new receipt is written and a framework file is then edited, it prints once again.
- [ ] AC-2: In a checkout without the test runner, the Stop run prints no reminder.
- [ ] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Decide with the operator whether to admit this change.
- [ ] Add the check and the once-per-receipt marker.
- [ ] Add the AC-1 and AC-2 tests, then run the touched files and the whole suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| hook | implementer | operator decision | Requirements 1 to 4 |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`

## Affected Architecture Docs

N/A: one advisory line in an existing hook.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The change itself, without the noise. |
| AC-2 | required | Targets must not see it. |
| AC-3 | required | Hook bytes are pinned. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-18 | Planned and recommended for parking. The receipt check exists and is cheap. | Guru investigation |
| 2026-10-18 | Parked. The Stop hook's stdout is not shown to the model. The check itself costs about 0.1 to 0.2 s, and the once-per-receipt marker works. | Fable plan review; Claude Code hooks docs; operator plan review |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | -------- |
| 2026-10-18 | Remind once per receipt, not on every turn. | A stale receipt is the normal state mid-implementation. | Every turn; noise the agent learns to ignore. Blocking Stop; would stop the agent mid-wave. |
| 2026-10-18 | Park; do not re-plan on Stop. | Stop stdout is not delivered to the model, and close already gates. | SessionStart or close dry-run, if a need appears. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The reminder adds little over close's own gate. | That is why parking is the recommendation. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
