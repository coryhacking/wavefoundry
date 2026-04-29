# MCP Wave Lifecycle State Mutations

Change ID: `1293b-feat mcp-wave-lifecycle`
Change Status: `stub`
Owner: Engineering
Status: stub
Last verified: 2026-04-29
Wave: `1293d mcp-server-foundation`
Depends on: `12926-feat wavefoundry-mcp-index` (MCP server and framework operation
tools must be implemented and stable before lifecycle tools are built on top)

## Rationale

Once the MCP server and framework operation tools (`wave.validate`, `wave.garden`,
`wave.sync_surfaces`) are in place, wave lifecycle operations can be exposed as
transactional tools that enforce the Wave Framework process without requiring agents
to know the correct sequence of steps.

Today an agent running "Prepare wave" must: read the prepare-wave prompt, understand
the required sequence, call validation scripts, check results, and manually advance
state. A transactional `wave.prepare()` tool does all of this in one call and only
advances state when the full precondition set passes.

The key design principle: **lifecycle tools are a state machine with embedded
validation, not thin doc-writing operations.** Each tool checks preconditions, runs
the relevant internal validations, advances state only on full pass, and returns
structured pass/fail with actionable error detail.

## Design Constraints (established in `12926-feat wavefoundry-mcp-index`)

- Each lifecycle tool runs lint and gardener internally before advancing state.
  Agents cannot skip validation by calling the tool directly.
- Partial state advance is not possible — a tool either succeeds fully or returns
  structured errors without modifying wave state.
- Standalone `wave.validate()` and `wave.garden()` remain available for diagnosis
  and manual recovery without advancing lifecycle state.
- Lifecycle tools delegate to the same `validate`/`garden`/`sync_surfaces`
  implementations; there is no duplicated validation logic.

## Planned Tool Surface (to be fully specified at planning time)

**`wave.create_wave(slug)`**
Creates a wave record at `docs/waves/<wave-id>/`. Returns wave ID and path.

**`wave.admit_change(wave_id, change_id)`**
Preconditions: change doc exists, has all required sections, not already admitted.
Writes admission. Returns structured confirmation or failure detail.

**`wave.remove_change(wave_id, change_id)`**
Removes an admitted change. Returns confirmation.

**`wave.prepare(wave_id)`**
Preconditions: wave exists, ≥1 admitted change, all change docs have required
sections and populated AC Priority tables.
Internal steps: gardener run → lint pass → section validation → AC Priority check.
On pass: marks wave as prepared. Returns structured summary.

**`wave.pause(wave_id)`**
Writes session handoff artifact at `docs/agents/session-handoff.md`. Returns path.

**`wave.review(wave_id)`**
Preconditions: wave is prepared or in implementation.
Runs required review lanes. Returns structured review results per lane.

**`wave.close(wave_id)`**
Preconditions: all ACs resolved, review lanes passed.
Internal steps: gardener run → lint pass → AC resolution check.
On pass: archives wave, updates workflow state. Returns archive path.

## Requirements

(To be fully authored at planning time. Stub entries below capture known constraints.)

1. All lifecycle tools are transactional: preconditions checked, validations run,
   state advanced only on full pass.
2. All lifecycle tools delegate validation to the same implementations used by
   standalone `wave.validate()` and `wave.garden()`.
3. Lifecycle tools return structured pass/fail — never raw script output.
4. This feature must not be planned or implemented until `12926-feat wavefoundry-mcp-index`
   has reached a stable implementation that can be depended on.

## Scope

(To be fully scoped at planning time.)

**In scope:** `wave.create_wave`, `wave.admit_change`, `wave.remove_change`,
`wave.prepare`, `wave.pause`, `wave.review`, `wave.close`.

**Out of scope:** Multi-wave coordination, concurrent wave support, remote/cloud
operation, rollback of closed waves.

## Acceptance Criteria

(To be authored at planning time.)

## Tasks

(To be authored at planning time.)

## Affected Architecture Docs

(To be determined at planning time.)

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|-------------|
| 2026-04-29 | Lifecycle tools embed validation internally | Enforces process correctness; agents cannot skip or mis-sequence steps | Thin wrappers leaving validation to agent |
| 2026-04-29 | Depends on 12926 MCP server being stable | Lifecycle tools build on framework operation tools; redesigning both in parallel creates rework risk | Implement concurrently (higher coordination cost) |

## Risks

| Risk | Mitigation |
|------|-----------|
| State machine complexity grows scope significantly | Plan fully before starting; do not implement from this stub |
| Edge cases in wave state transitions not covered by lint/gardener | Identify all precondition checks at planning time; add targeted validators rather than relying solely on existing scripts |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
