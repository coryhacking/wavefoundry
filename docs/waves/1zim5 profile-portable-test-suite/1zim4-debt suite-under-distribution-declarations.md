# The Framework Test Suite Runs With a Distribution's Tool Declarations

Change ID: `1zim4-debt suite-under-distribution-declarations`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zim5 profile-portable-test-suite

## Rationale

From the downstream "Tool-name seams" note against `v1.28.0`: with one alias declared in `mcp_tool_extensions`, the suite gains 34 stable failures. Most are expected (stock-surface, golden, roster-count and census tests pin the empty declaration). Nineteen are test doubles of the MCP surface, a recorder whose tool table holds plain functions or a fake without `_tool_manager`, which break in `_install_served_names` when it calls `model_copy` on each canonical tool. A distribution's declarations then mask real regressions in its own suite run.

## Requirements

1. **Stock-surface tests pin the stock declaration.** Tests whose subject is the shipped (empty) declaration run with the declaration patched empty, through one shared helper, so a distribution's declarations do not change their outcome.
2. **Test doubles behave like FastMCP.** The MCP-surface doubles build on a real `FastMCP` instance (or a shared double exposing the same `_tool_manager._tools` of `Tool` objects), so declaration machinery runs against them as against the server.
3. **A declared-alias run.** The second-profile run mode from `1zim1` can also apply a sample declaration (one alias, one parameter-mapped alias once `1zim0` lands) so the suite proves it holds with declarations present.
4. **Platforms.** Windows, macOS, Linux and WSL2 behave the same.
5. **Transition.** Test infrastructure only; no CHANGELOG entry.

## Scope

**Problem statement:** a distribution's own tool declarations break unrelated tests in the framework suite, masking real regressions.

**In scope:**

- The shared empty-declaration helper; the MCP-surface doubles; the sample-declaration option of the profile run.

**Out of scope:**

- Production changes to extension serving (`1zim0`).

## Acceptance Criteria

- [ ] AC-1: with a sample alias declared, the suite passes: stock-surface tests patch the declaration empty through the shared helper, and no test double fails in `_install_served_names`.
- [ ] AC-2: removing the helper from a stock-surface test makes it fail under the sample declaration (the helper is load-bearing).
- [ ] AC-3: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Empty-declaration helper and its adoption.
- [ ] FastMCP-backed doubles.
- [ ] Sample-declaration option.
- [ ] Tests.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Declarations portability | implementer | 1zim1 runner mode | |
| Review | code-reviewer, qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/` (stock-surface tests and MCP-surface doubles)
- `.wavefoundry/framework/scripts/run_tests.py` (sample-declaration option)

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` (one line).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Distribution suites stay meaningful |
| AC-2 | required | Pins are real |
| AC-3 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Planned from the downstream note's test-suite section (34 stable failures with one alias: 19 test doubles plus expected stock-surface, golden, roster-count and census pins). Not yet re-measured upstream; the implementation starts with that measurement | Downstream report |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Separate from `1zim1` | Different mechanism (declarations, not record profile); shares the runner mode | Fold into `1zim1` |

## Risks

| Risk | Mitigation |
| --- | --- |
| A double that must stay minimal for speed | A shared FastMCP-backed double keeps it cheap |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
