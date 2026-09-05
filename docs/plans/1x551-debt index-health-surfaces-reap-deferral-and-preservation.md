# Surface Reap Deferral and Preservation Through index_build_status and index_health

Change ID: `1x551-debt index-health-surfaces-reap-deferral-and-preservation`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
Wave: TBD

## Rationale

Recorded during the delivery review of wave `1x54z` (SEC-DEL-1 and
SEC-RV1-1). Since that wave a build that defers a mass-absent Lance reap or
preserves a walk-shadowed subtree says so in the `build_index` result
(`stranded_reap_deferred`, `stranded_reap_preserved`), on stderr, and in the
index-state log. That result is the Python return value only: the registered
`index_build` tool spawns the build detached and returns a spawn
acknowledgement, `index_build_status` reads the build log for the completion
marker and stats, and `index_health` reads the persisted index state, none of
which carries either state. Under an MCP-driven or hook-driven build an
operator cannot see that the index is knowingly serving rows as of the last
readable build, nor that a deferral has persisted across builds, without
opening the logs. The deferral is recomputed each build and never persisted,
so a diagnostic needs an epoch-free record of it.

## Requirements

1. A build that defers a stranded reap or preserves a shadowed subtree SHALL
   persist both per-table summaries in the index state store outside the
   build epoch, replaced on every build and cleared when neither applies.
2. `index_build_status` SHALL report the persisted summaries for the most
   recent completed build.
3. `index_health` SHALL raise an advisory diagnostic while a deferral or a
   preservation persists, naming the tables, the counts, the build that
   recorded it, and the remedy the build log names.
4. Tests SHALL pin that the diagnostic appears after a deferred build and
   clears after a build with nothing deferred or preserved, through the
   registered tool responses.

## Scope

**Problem statement:** the deferred and preserved states of the eligibility
reap are visible only in the Python build result and the logs; the registered
tool surface an agent or operator uses shows neither.

**In scope:**

- Epoch-free persistence of the two summaries in the index state store.
- `index_build_status` and `index_health` reporting in `server_impl.py`.
- Tests through the registered tool responses.

**Out of scope:**

- The reap's classification and breaker policy (wave `1x54z`).
- Relaying the whole `build_index` result through `index_build` (the tool is a
  detached spawn by design).

## Acceptance Criteria

- [ ] AC-1: After a deferred zero-change build, `index_build_status` reports the per-table deferral counts of that build.
- [ ] AC-2: After a walk-shadowed build, `index_health` carries an advisory diagnostic naming the preserved counts and the remedy.
- [ ] AC-3: After a build with nothing deferred or preserved, both surfaces report nothing and the diagnostic is absent.

## Tasks

- [ ] Persist the two summaries epoch-free in the state store at both build seams.
- [ ] Read them in `index_build_status_response` and the `index_health` diagnostics.
- [ ] Pin the appear-then-clear behaviour through the registered tools.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                        |
| ---------- | ----------- | ---------- | -------------------------------------------- |
| persist    | implementer | —          | Follow the `server_impl.py` playbook memory. |
| surface    | implementer | persist    | Two read sites, one diagnostic code.         |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` item 15 (the follow-on sentence
becomes the shipped behaviour) and `docs/specs/mcp-tool-surface.md` for the
two tool responses.

## AC Priority


| AC   | Priority | Rationale                                            |
| ---- | -------- | ---------------------------------------------------- |
| AC-1 | required | The status surface is where a build's outcome is read. |
| AC-2 | required | The health surface is where a persisting condition is read. |
| AC-3 | required | A stale diagnostic is worse than none.                |


## Progress Log


| Date       | Update                                                                                                   | Evidence                                            |
| ---------- | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 2026-09-04 | Filed from the `1x54z` delivery review (SEC-DEL-1 second half; SEC-RV1-1 confirmed no registered tool relays the result). | Wave `1x54z` events ledger, findings SEC-DEL-1 and SEC-RV1-1. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk                                                             | Mitigation                                                      |
| ---------------------------------------------------------------- | --------------------------------------------------------------- |
| A persisted summary outlives the condition after a manual rebuild. | Every build replaces or clears it; a rebuild is a build.        |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
