# Wave Close Secrets Gate

Change ID: `1p3rp-enh wave-close-secrets-gate`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-06
Wave: `1p3rm scan-rules-secrets-detection`

## Rationale

Without a close gate, a wave can be closed while `docs/scan-exceptions.json` still contains unresolved findings. The lint check and agent review surface findings but neither currently prevents close. This change adds a secrets gate to `wave_close`: `pending` entries hard-block close with no override; `confirmed-secret` entries soft-block with a mandatory per-close operator acknowledgment. The acknowledgment is wave-scoped and persisted in `acknowledged_for_wave` — a different wave ID triggers re-acknowledgment.

## Requirements

1. `wave_close` reads `docs/scan-exceptions.json` before executing. If the file is absent, the gate passes silently.
2. If any entry has `status: pending`, close is hard-blocked. The error output lists each blocking entry (file, line, rule ID) and instructs the operator to run the security reviewer to resolve them.
3. If any entry has `status: confirmed-secret` and `acknowledged_for_wave` does not match the current wave ID, close is soft-blocked. The gate fails with a structured error listing each unacknowledged entry (file, line, redacted matched text, rule ID, `override_reason` if present) and instructions for resolution.
4. The gate error output format for a soft-block:

   ```
   SECRETS GATE — <N> confirmed secret(s) require acknowledgment for wave <wave_id>:

     [<id>] <file>:<line>  rule: <rule_id>
     Matched: <redacted_text>
     Override reason: <override_reason or "(none)">

   To proceed: run the security reviewer, which will present each entry for operator acceptance.
   The security reviewer will write acknowledged_for_wave: "<wave_id>" to docs/scan-exceptions.json
   for each entry the operator accepts. Then re-run wave_close.
   ```

5. The acknowledgment is wave-scoped and persisted: the security reviewer agent writes `acknowledged_for_wave: "<wave_id>"` to the entry in `docs/scan-exceptions.json` after the operator accepts. Closing a different wave clears the acknowledgment requirement — the gate checks that `acknowledged_for_wave` matches the current wave ID, not just that it is set.
6. `confirmed-secret` entries with no `override_reason` field still soft-block; the gate error notes the absence and reminds the operator to add one before or after acknowledgment.
7. `confirmed-secret` entries where `acknowledged_for_wave` matches the current wave ID pass the gate silently.
8. The gate check is implemented in `server_impl.py` within the `wave_close` handler, after wave-state validation but before any close mutations are written.
9. The gate behavior is documented in the `wave_close` MCP tool description so agents know to expect the prompt.

## Scope

**Problem statement:** A wave with unresolved credential findings can be closed today. The gate enforces resolution before close without preventing legitimate carries of known issues.

**In scope:**

- `server_impl.py` — secrets gate logic in `wave_close` handler
- `wave_close` MCP tool description — gate behavior documentation
- Framework tests for gate behavior

**Out of scope:**

- The exceptions file schema — defined in `1p3rn`
- The lint validator — defined in `1p3rn`
- Security reviewer pre-scope step — defined in `1p3ro`
- Gate behavior for PHI/PII/PCI categories — follow-on wave

## Acceptance Criteria

- [x] AC-1: `wave_close` with no `docs/scan-exceptions.json` file passes the gate without error.
- [x] AC-2: `wave_close` with one or more `pending` entries is hard-blocked; error lists each entry by file, line, and rule ID.
- [x] AC-3: `wave_close` with one or more `confirmed-secret` entries lacking `acknowledged_for_wave` matching the current wave ID fails with a structured error listing each entry and resolution instructions.
- [x] AC-4: After the security reviewer writes `acknowledged_for_wave: "<wave_id>"` to all `confirmed-secret` entries and `wave_close` is re-run, close proceeds.
- [x] AC-5: A `confirmed-secret` entry with `acknowledged_for_wave` set to a different wave ID still soft-blocks (acknowledgment is wave-scoped).
- [x] AC-6: A `confirmed-secret` entry with `acknowledged_for_wave` matching the current wave ID passes the gate silently.
- [x] AC-7: A `confirmed-secret` entry with no `override_reason` still soft-blocks; gate error notes the absence.
- [x] AC-8: Gate logic executes after wave-state validation but before any close mutations.
- [x] AC-9: `wave_close` MCP tool description documents the gate behavior.
- [x] AC-10: Framework tests cover: no-file pass, pending hard-block, confirmed-secret soft-block (no acknowledgment), confirmed-secret passes when acknowledged_for_wave matches current wave, confirmed-secret blocks when acknowledged_for_wave is a different wave ID.

## Tasks

- [x] Open framework edit gate (`wave_gate_open(gate="framework_edit_allowed")`)
- [x] Add secrets gate logic to `wave_close` handler in `server_impl.py`
- [x] Update `wave_close` MCP tool description with gate behavior
- [x] Close framework edit gate (`wave_gate_close(gate="framework_edit_allowed")`)
- [x] Write framework tests in `tests/test_server_tools.py` for gate behavior
- [x] Run full framework test suite; confirm no regressions

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| server_impl.py gate logic | software-engineer | `1p3rn` complete (schema and path constants stable) | Framework edit gate wraps this work |
| tool description update | software-engineer | gate logic | Update after logic is implemented |
| tests | qa-reviewer | gate logic | Test after implementation is complete |

## Serialization Points

- Framework edit gate must be open for the duration of `server_impl.py` edits and closed immediately after.

## Affected Architecture Docs

N/A — change is confined to `wave_close` handler in `server_impl.py` and MCP tool description. No boundary, schema, or flow architecture impact beyond the gate behavior already described in the tool doc.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Absent file must not break close for new projects |
| AC-2 | required | Pending hard-block is the core enforcement |
| AC-3 | required | Soft-block prompt must show full context |
| AC-4 | required | Acknowledgment must allow proceed |
| AC-5 | required | Non-acknowledgment must abort |
| AC-6 | required | Wave-scoped acknowledgment — different wave requires re-acknowledgment |
| AC-7 | important | Missing override_reason should be nudged |
| AC-8 | required | Gate must not run after mutations |
| AC-9 | important | Tool description is the agent's only pre-briefing on gate behavior |
| AC-10 | required | Tests are the verification gate |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| | | |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-06 | pending = hard block, no override | Unreviewed findings have no known disposition; operator must run security reviewer first | Soft block for pending — rejected: operator could bypass without reviewing |
| 2026-06-06 | confirmed-secret = soft block with wave-scoped persistent acknowledgment | Allows legitimate carry of known issues (e.g. mid-remediation) without silently suppressing the signal. Acknowledgment is written to `acknowledged_for_wave`; closing a different wave requires re-acceptance. | Permanent override written to file — rejected: removes per-close discipline; hard block always — rejected: blocks legitimate mid-remediation waves |
| 2026-06-06 | Fail-with-instructions + agent-prompt + acknowledged_for_wave field | MCP tool calls have no TTY stdin; interactive "type acknowledge secrets" is unsatisfiable in agent context. wave_close fails with a structured error; agent presents entries to operator and writes acknowledged_for_wave on acceptance. Wave-scoped acknowledgment preserves per-close discipline without TTY dependency | Boolean wave_close parameter — rejected: leaks acknowledgment concern into tool API; TTY prompt — rejected: not available in MCP context |

## Risks

| Risk | Mitigation |
|---|---|
| Operator adds override_reason and forgets to actually remediate | Re-prompt on every close keeps the issue visible; override_reason must state the remediation plan |
| Gate adds latency to every close | File read is fast; gate exits immediately when no entries or all `confirmed-secret` entries have matching `acknowledged_for_wave` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
