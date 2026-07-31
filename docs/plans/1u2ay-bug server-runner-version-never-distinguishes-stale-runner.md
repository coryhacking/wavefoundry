# server_runner_version Cannot Distinguish a Stale Runner From a Current One

Change ID: `1u2ay-bug server-runner-version-never-distinguishes-stale-runner`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-31
Wave: TBD

## Rationale

`SERVER_RUNNER_VERSION` is hardcoded to `"1"` in `server.py` (canonical, with a re-exported alias
in `server_impl.py`) and has never been bumped, including across the 1.15.0 protocol-bridge
release that replaced the runner file. Under the hot-reload design the runner process stays loaded
while `server_impl` reloads, and `server_runner_version` in `wf_server_info` exists precisely to
tell an operator or agent that the long-lived runner process is stale relative to disk and a full
host restart is needed. With the constant frozen at `"1"`, a pre-1.15 runner and a current one
report identically, so the field carries no signal.

Field-observed twice: an earlier unfiled finding noted the constant never bumps, and the 2026-07-31
1.14.0 to 1.15.0 bridge upgrade in a target repository reported `server_runner_version: "1"` after
a full restart onto the new runner, indistinguishable from the pre-restart value. Note this field
is distinct from the upgrade protocol (`upgrade_bridge_bootstrap.PROTOCOL = 2`), which versions the
upgrade boundary, not the MCP runner.

## Requirements

1. `wf_server_info` exposes a runner identity that changes whenever the on-disk runner changes,
   captured at process launch, so a running-but-stale runner is detectable by comparing the
   reported value against the current disk state.
2. The mechanism must not depend on a human remembering to bump a constant, or, if a manual
   constant is retained, a test must fail whenever `server.py` content changes without a bump
   (the `GRAPH_BUILDER_VERSION` discipline).
3. In-process `wf_reload_mcp` must not change the reported runner identity (the runner is exactly
   the part a reload does not replace); only a real process restart may change it.
4. The response should make staleness legible, not just different: when the runner-at-launch
   identity differs from the current on-disk runner, `wf_server_info` surfaces an explicit
   stale-runner indication with the restart instruction.

## Scope

**Problem statement:** the runner-version field meant to signal "restart required, your runner is
stale" is a frozen constant, so it can never fire.

**In scope:**

- `.wavefoundry/framework/scripts/server.py` (identity capture at launch)
- `.wavefoundry/framework/scripts/server_impl.py` (`wf_server_info` reporting and the re-exported
  alias)
- Tests in `test_server_tools.py` that pin the current `"1"` behavior

**Out of scope:**

- The upgrade protocol constant (`upgrade_bridge_bootstrap.PROTOCOL`) and bridge selection logic
- Any host-side reconnect automation

## Design Options (decide at Prepare)

1. **Derive at launch from content:** runner records a short hash of its own `server.py` bytes at
   process start; `wf_server_info` compares against the current on-disk hash and reports both plus
   a `runner_stale` boolean. No manual bumping, requirement 2 satisfied structurally.
2. **Derive from framework VERSION at launch:** runner records the `.wavefoundry/framework/VERSION`
   it was launched under. Simpler to read, but misses runner changes within a version during
   development and reports staleness even when `server.py` itself did not change.
3. **Manual constant plus bump-guard test:** keep the constant, add a fixture hash test that fails
   when `server.py` changes without a bump. Preserves the current shape; relies on suite discipline.

Option 1 is the recommendation: it measures exactly the artifact whose staleness matters.

## Acceptance Criteria

- [ ] AC-1: After replacing `server.py` on disk while a runner process launched from the old bytes
  is still serving, `wf_server_info` reports a stale-runner indication naming the full-restart
  recovery.
- [ ] AC-2: An in-process `wf_reload_mcp` does not change the reported runner identity; a fresh
  process launch from the new bytes reports current, with no stale indication.
- [ ] AC-3: The mechanism requires no manual constant bump, or a guard test fails whenever
  `server.py` content changes without one.
- [ ] AC-4: Existing `wf_server_info` consumers (tests pinning `server_runner_version`) are updated
  coherently; full framework suite passes.

## Tasks

- [ ] Decide the identity mechanism at Prepare (options above)
- [ ] Implement capture-at-launch and comparison reporting in `wf_server_info`
- [ ] Update or replace the tests pinning the frozen constant
- [ ] Run the full framework test suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                              |
| ---------- | ----------- | ---------- | ---------------------------------- |
| fix        | implementer | —          | Small, two files plus their tests |


## Serialization Points

- `server.py` / `server_impl.py` (single coordinated edit)

## Affected Architecture Docs

Possibly `docs/architecture/` MCP hot-reload notes if they document the runner-version contract;
audit at Prepare. Otherwise N/A: reporting-only change inside the server surface.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported defect: the staleness signal can never fire |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date       | Decision                        | Reason                                        | Alternatives     |
| ---------- | ------------------------------- | --------------------------------------------- | ---------------- |
| 2026-07-31 | Filed from field observation    | Twice-observed; the field is currently inert  | Leave unfiled    |


## Risks


| Risk                                                        | Mitigation                                                    |
| ----------------------------------------------------------- | -------------------------------------------------------------- |
| Hash-at-launch reads disk state that changes mid-upgrade    | Capture once at process start; comparison is read-only + fail-safe |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
