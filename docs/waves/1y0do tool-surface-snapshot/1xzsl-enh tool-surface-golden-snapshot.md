# Golden Snapshot Of The Public MCP Tool Surface

Change ID: `1xzsl-enh tool-surface-golden-snapshot`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-14
Wave: `1y0do tool-surface-snapshot`

## Rationale

**Brief.** Goal: make "no unintended public change" provable before any server refactor or layout change lands. Audience: framework maintainers and the reviewers of waves `1y0h1 tool-registry-dispatch`, `1y0h2 handler-module-split`, and `1y0gz record-layout-roots`. Approach: a committed golden file of every registered tool's name, roster tier, input schema, and annotations, checked by the ordinary test suite. Constraints: no production behavior change; the existing test doubles and `mcp._tool_manager._tools` census pattern are reused. Success: a schema drift anywhere on the 90-tool surface fails one named test with a readable diff.

The RFC in `docs/reports/wavefoundry-modularity-rfc.md` and its kickoff companion ask for this as slice 0. Verification against the current tree found that two of the three slice-0 guards already exist: the roster parity census (`test_roster_matches_registration_census`) and the wrapper-order contract (`test_upgrade_guard_is_outermost_and_never_waits_on_lifecycle_lock`). Only the whole-surface schema snapshot is missing. Today the closest guard is one whole-registry invariant (no `kwargs` published, `additionalProperties: false`) plus targeted per-tool parameter assertions, so a renamed parameter, a dropped tool, or a changed `destructiveHint` on most tools passes silently.

Re-verified 2026-09-17 against four intervening commits (`1y3og setup-local-reconciliation` through `1y6hg python-runtime-deprecation-advisory`): the registered tool count is still exactly 90, and no `@mcp.tool` was added or removed. `1y3og` folded its new setup-readiness assessment into the *existing* `index_health` tool's response data (`server_impl.py:33141-33146` sets `result["data"]["setup_readiness"]`) rather than registering a new tool. That is a response-shape addition, not an input-schema change, and this change's snapshot is scoped to input schemas, tiers, and annotations by Requirement 1 — so it is correctly out of this snapshot's coverage, not a gap the four commits opened.

## Requirements

1. A test under `.wavefoundry/framework/scripts/tests/` boots `register_mcp_surface` against the existing stub handler pattern and serializes every registered tool to a deterministic JSON document: `name`, roster tier from `mcp_tool_roster.TOOL_TIERS`, `inputSchema` (properties with their JSON types, `required`, `additionalProperties`), and `annotations`. Descriptions are excluded (see Decision Log).
2. The serialization is byte-stable: keys sorted, tools sorted by name, two consecutive generations in one process are identical.
3. The golden file is committed at `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden.json`. The test compares the live serialization to the file and fails with a diff that names each added tool, removed tool, and changed schema key per tool.
4. Regeneration is explicit: setting `WF_UPDATE_TOOL_SURFACE_GOLDEN=1` rewrites the file and the test then passes; without it the test never writes.
5. Runner survivor tools (`wf_reload_mcp` and the rest of `mcp_tool_roster.RUNNER_TOOLS`) are not part of `register_mcp_surface`; the test asserts the registered set plus `RUNNER_TOOLS` equals the roster's key set, in both directions, as a runtime complement to the existing AST census.
6. A wrapper-order test proves by behavior that the three post-registration wrappers compose as cost innermost, lifecycle lock middle, upgrade-publication guard outermost, matching the call order at the end of `register_mcp_surface` and the comment that explains it. The existing guard-is-outermost test remains.
7. `docs/contributing/build-and-verification.md` documents when the golden must change (any intentional public schema change) and how to regenerate it.
8. No file under `.wavefoundry/framework/scripts/` outside `tests/` changes.

## Scope

**Problem statement:** The public tool surface can drift without a failing test, which makes every behavior-preserving refactor unprovable.

**In scope:**

- The golden snapshot test, fixture, regeneration path, and diff reporting.
- The bidirectional runtime roster parity assertion.
- The behavioral wrapper-order test.
- The contributing-doc note.

**Out of scope:**

- Any production code change, including marking wrappers with inspectable attributes (that belongs to `1y0be-ref tool-registry-and-wrapper-chain`).
- Snapshotting tool descriptions or `wf_help` catalog prose.
- Snapshotting MCP resources and resource templates (a follow-up if the registry wave touches them).

## Acceptance Criteria

- [ ] AC-1: `tool-surface-golden.json` exists, and generating the serialization twice in one test run yields byte-identical output.
- [ ] AC-2: A test that mutates a copy of the live serialization (one added parameter, one removed tool, one flipped annotation) sees the comparison fail with a message naming the tool and the changed key in each case.
- [ ] AC-3: With `WF_UPDATE_TOOL_SURFACE_GOLDEN=1` the test rewrites the fixture and passes; without it, a stale fixture fails and the fixture file is unchanged after the run.
- [ ] AC-4: The parity test fails when a name is added to the roster without registration and when a tool is registered without a roster entry, and passes on the current tree.
- [ ] AC-5: The wrapper-order test fails when the three wrappers are applied in any of the other five orders and passes on the current tree.
- [ ] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Write the serializer helper in the test module, reusing the stub-handler boot used by `WaveMcpReloadTests`.
- [ ] Generate and commit the golden fixture from the current tree.
- [ ] Implement the comparison with per-tool, per-key diff output and the regeneration environment flag.
- [ ] Add the bidirectional roster parity assertion including `RUNNER_TOOLS`.
- [ ] Add the behavioral wrapper-order test with monkeypatched inner functions recording call sequence.
- [ ] Add the mutation-based negative tests for AC-2, AC-4, AC-5.
- [ ] Update `docs/contributing/build-and-verification.md`.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| snapshot-test  | implementer | —            | serializer, fixture, diff, regen flag |
| parity-order   | implementer | snapshot-test | roster parity and wrapper order share the boot fixture |
| docs           | implementer | snapshot-test | contributing note |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/`
- `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` gains a short entry for the golden tool-surface guard as a verification seam that later refactor waves depend on. No other architecture doc changes: no module boundary, contract, or data path moves.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Determinism is the whole value of a golden file |
| AC-2 | required  | Proves the guard detects the three drift classes |
| AC-3 | required  | Regeneration must be deliberate, never accidental |
| AC-4 | important | Runtime parity complements the existing AST census |
| AC-5 | required  | The registry wave will replace the wrapper application and must be judged against this |
| AC-6 | required  | Standard change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-14 | Change planned and admitted to `1y0do tool-surface-snapshot` | this document |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-14 | Snapshot name, tier, input schema, and annotations; exclude descriptions | Descriptions are prose that changes with documentation edits; including them turns every wording fix into a golden regeneration and trains reviewers to rubber-stamp diffs | (a) Include descriptions: highest coverage, highest churn. (b) Hash descriptions only: detects change but the diff is unreadable. Selected: exclude, revisit if a description regression ever ships |
| 2026-09-14 | Committed JSON fixture compared by a test, not a snapshot library | Zero new dependencies; the suite runs with stdlib only and ships nowhere (tests are excluded from the pack) | Snapshot library: nicer diffs, new dependency in a project that keeps its runtime local and minimal |
| 2026-09-14 | Prove wrapper order by behavior, not by attributes on the wrapped callables | Keeps this change test-only; attributes are a production change the registry wave can add when it owns the middleware chain | Inspectable attributes now: simpler test, but violates the no-production-change rule of this slice |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| FastMCP internals (`_tool_manager._tools`) change shape in a dependency bump | The serializer is one helper; the existing tests already depend on the same attribute, so the blast radius is shared and visible |
| Reviewers regenerate the golden reflexively | The contributing note states that a golden diff is a public contract change and must be named in the change doc that causes it |
| The fixture path becomes part of the framework test receipt hash | Intended: any surface change invalidates the receipt and forces a fresh green run before close |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
