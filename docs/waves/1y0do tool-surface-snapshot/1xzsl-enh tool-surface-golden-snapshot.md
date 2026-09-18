# Golden Snapshot Of The Public MCP Tool Surface

Change ID: `1xzsl-enh tool-surface-golden-snapshot`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-17
Wave: `1y0do tool-surface-snapshot`

## Rationale

**Brief.** Goal: make "no unintended public change" provable before any server refactor or layout change lands. Audience: framework maintainers and the reviewers of waves `1y0h1 tool-registry-dispatch`, `1y0h2 handler-module-split`, and `1y0gz record-layout-roots`. Approach: a committed golden file of every registered tool's name, roster tier, input schema, and annotations, checked by the ordinary test suite. Constraints: no production behavior change; the existing test doubles and `mcp._tool_manager._tools` census pattern are reused. Success: a schema drift anywhere on the complete registered surface fails one named test with a readable diff.

The RFC in `docs/reports/wavefoundry-modularity-rfc.md` and its kickoff companion ask for this as slice 0. Verification against the current tree found that two of the three slice-0 guards already exist: the roster parity census (`test_roster_matches_registration_census`) and the wrapper-order contract (`test_upgrade_guard_is_outermost_and_never_waits_on_lifecycle_lock`). Only the whole-surface schema snapshot is missing. Today the closest guard is one whole-registry invariant (no `kwargs` published, `additionalProperties: false`) plus targeted per-tool parameter assertions, so a renamed parameter, a dropped tool, or a changed `destructiveHint` on most tools passes silently.

Re-verified 2026-09-17 against four intervening commits (`1y3og setup-local-reconciliation` through `1y6hg python-runtime-deprecation-advisory`): the implementation registration and runner survivors together form the complete public roster; counts are derived from actual registration, not text occurrences of `@mcp.tool`. `1y3og` folded its new setup-readiness assessment into the *existing* `index_health` tool's response data (`server_impl.py:33141-33146` sets `result["data"]["setup_readiness"]`) rather than registering a new tool. That is a response-shape addition, not an input-schema change, and this change's snapshot is scoped to input schemas, tiers, and annotations by Requirement 1 — so it is correctly out of this snapshot's coverage, not a gap the four commits opened.

## Requirements

1. A test under `.wavefoundry/framework/scripts/tests/` boots the real `server.build_server` in a temporary repository with `server_impl.build_handler` stubbed, adapting the existing runner tests with a new handler stub (those tests normally use the real handler). It serializes every registered tool, including runner survivors, to a deterministic JSON document: `name`, roster tier from `mcp_tool_roster.TOOL_TIERS`, the complete `inputSchema`, and `annotations`. Preserve defaults, enums, composition, references, definitions and every validation constraint. Exclude tool descriptions and prose `description` metadata at schema nodes only; never remove a property or definition merely because its name is `description`. No model loading, index build, monitor startup or real repository writes are allowed.
2. The serialization is byte-stable: keys sorted, tools sorted by name, explicit UTF-8 and LF newlines on every platform; two consecutive generations in one process are identical.
3. The golden file is committed at `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden.json`. The test compares the live serialization to the file and fails with a diff that names each added tool, removed tool, and changed schema key per tool.
4. Regeneration is explicit: setting `WF_UPDATE_TOOL_SURFACE_GOLDEN=1` rewrites the file and the test then passes; without it the test never writes. Regeneration and stale-fixture negative tests use a temporary fixture path and scoped environment patch; they never alter the committed fixture or leak the update flag into another test.
5. The complete set returned by `build_server` equals the roster key set in both directions, including every `RUNNER_TOOLS` member. Runner survivor schemas are captured from actual registration, not manufactured from the roster. Retain an implementation-side assertion that its registered set plus `RUNNER_TOOLS` equals the roster, as a runtime complement to the existing AST census; do not freeze a literal tool count.
6. A wrapper-order test proves by behavior that the three post-registration wrappers compose as cost innermost, lifecycle lock middle, upgrade-publication guard outermost, matching the call order at the end of `register_mcp_surface` and the comment that explains it. The existing guard-is-outermost test remains. Invoke a tool wrapped by all three wrappers through the actual registered callable, with their inner effects instrumented. Negative controls change the real registration application order in an isolated test copy for all five wrong permutations; testing a separately assembled expected chain is insufficient.
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

- [x] AC-1: `tool-surface-golden.json` exists, and generating the serialization twice in one test run yields byte-identical output.
- [x] AC-2: A test that mutates a copy of the live serialization (one added parameter, one removed tool, one flipped annotation, a nested validation/default change, and a survivor-schema change) sees the comparison fail with a message naming the tool and the changed key in each case. A prose-only description edit does not change the snapshot, while an input property named `description` remains covered.
- [x] AC-3: With `WF_UPDATE_TOOL_SURFACE_GOLDEN=1` the test rewrites the fixture and passes; without it, a stale fixture fails and the fixture file is unchanged after the run. Exercise both branches against temporary fixtures and restore the environment afterward.
- [x] AC-4: The parity test fails when a name is added to the roster without registration and when a tool is registered without a roster entry, and passes on the current tree, including actual runner survivors.
- [x] AC-5: The wrapper-order test fails when the three wrappers are applied in any of the other five orders and passes on the current tree.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write the serializer helper in the test module, adapting the `WaveMcpReloadTests` runner boot with a new `build_handler` stub.
- [x] Generate and commit the golden fixture from the current tree.
- [x] Implement the comparison with per-tool, per-key diff output and the regeneration environment flag.
- [x] Add the bidirectional roster parity assertion including `RUNNER_TOOLS`.
- [x] Add the behavioral wrapper-order test with monkeypatched inner functions recording call sequence.
- [x] Add the mutation-based negative tests for AC-2, AC-4, AC-5.
- [x] Update `docs/contributing/build-and-verification.md` and the verification-seam entry in `docs/architecture/testing-architecture.md`.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

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
| 2026-09-17 | Delivery review, cycle 1. Lanes: code-reviewer APPROVE (three mutants killed), qa-reviewer APPROVE-WITH-NOTES, red-team primer NO-BLOCKING-FINDING (could not fool the guard; `list_tools` resolves to the same table the test reads, so the private-attribute choice is an accepted documented risk; two-process and two-hash-seed determinism runs green). One real finding from qa: the AC-3 leak assertion checked absolute absence of `WF_UPDATE_TOOL_SURFACE_GOLDEN`, so the exact regeneration command the contributing doc prescribes made that test fail. Repaired under the gate: the test now records the flag's presence at entry and asserts it is unchanged at exit. Verified green with and without the flag; fixture bytes unchanged by the flagged run. Test-module fingerprint moved from `e18320002e343ed1` to `2d574862d17f51de`; qa reverifies independently; full suite re-run for a fresh receipt. Editorial note from qa: the module is untracked until committed. | lane reports; focused runs with and without the flag |
| 2026-09-17 | Full suite green after all edits: 9,165 tests across 98 files, receipt `result: ok` written 2026-09-17T23:43Z; docs validation passes; no stray artifacts; framework edit gate closed. AC-6 marked. | `run_tests.py` log; `.wavefoundry/framework/test-cache.json` |
| 2026-09-17 | Implemented. `tests/test_tool_surface_golden.py` (13 tests, three classes) and `tests/fixtures/tool-surface-golden.json` (90 tools: 89 implementation plus the `wf_reload_mcp` survivor; `wf_review_event.operator_handle` from wave 1y9sv is in the fixture). Serializer canonicalizes: prose `description` stripped except as a name under `properties`/`$defs`, `required` arrays sorted, annotations via `model_dump(exclude_none=True)`, UTF-8 and LF. Wrapper-order subject is `wf_add_change` (in all three wrapper sets); order is observed as `guard, lock_enter, fn, cost, lock_exit` on a passing probe and `guard` alone on a blocking probe; all five wrong permutations differ. Landing rule, each mutant restored byte-for-byte afterward: (1) fixture `wf_help.annotations.readOnlyHint` flipped, killed by `test_live_surface_matches_committed_golden`; (2) regeneration guard loosened to always write, killed by `test_regeneration_is_explicit_and_isolated`; (3) `parity_errors` loosened to return nothing, killed by `test_parity_fails_in_both_directions`; (4) production wrapper application order swapped (guard before lock) in `server_impl.py`, killed by `test_production_order_is_cost_inner_lock_middle_guard_outer`. Gapfill: code exploration went through `code_read`/`code_definition`/`code_keyword`; shell `grep` was used for a handful of line-anchored lookups in the 1.6 MB `server_impl.py` where the structural parser declines the file, and for executed probes. | focused run `--file test_tool_surface_golden.py`: 13 passed; mutant script output |
| 2026-09-17 | Readback before editing. Behavior: a new test module `tests/test_tool_surface_golden.py` boots `server.build_server` on a temp repo with `build_handler` patched to a stub, serializes every registered tool (name, roster tier, input schema with schema-node `description` stripped, annotations via `model_dump`) sorted and byte-stable, compares to the committed fixture `tests/fixtures/tool-surface-golden.json`, and regenerates only under `WF_UPDATE_TOOL_SURFACE_GOLDEN=1`. Parity: registered set equals roster set both ways, survivors included. Wrapper order: instrument the lock context manager, the publication block reader, and the cost checkpoint reader, invoke `wf_add_change` (in all three wrapper sets; the five cost-exempt lifecycle tools are not valid subjects) through the registered callable, and run all six permutations by rebinding the three `_wrap_*` names before a fresh `register_mcp_surface`. ACs 1 to 6. Boundary: no file under `scripts/` outside `tests/` changes. Files: the new test module, the fixture, `docs/contributing/build-and-verification.md`, `docs/architecture/testing-architecture.md`. | readiness lanes code-reviewer and qa-reviewer, both approve-with-notes; live probe: 89 registered plus 1 survivor, zero `description` keys in any live input schema |
| 2026-09-17 | Prepare review clarified full runner coverage, schema fidelity, real-chain mutation controls and isolated regeneration. No production changes authorized. | Independent readiness report and actual stubbed runner probe. |
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
