# Document and Test `kind:"module"` Fan-Out Semantics

Change ID: `1312f-enh module-fan-out-semantics-doc-and-test`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Solaris field report (2026-06-01) on `1.2.0+312f`: when investigating `StatusBarManager (module)` with `fan_out: 77`, Solaris had to read the indexer source to figure out what the number actually counted. The `wave_graph_report.fan_out` docstring describes the metric as "symbols that call the most others" — which is accurate for function/method nodes but misleading for file/module nodes, where the `count` aggregates `defines` + `imports` + outgoing `calls` from symbols inside the file that get attributed to the file's node.

This change is the cheapest, highest-clarity win: docstring fix on `wave_graph_report` + a unit test on a known small file that asserts the exact `count` decomposition for a module entry, so future regressions surface immediately and operators can read the doc without reaching for source.

## Requirements

1. **Update the `wave_graph_report` docstring** for `fan_out` (and the new `file_hubs` section from the companion change) to explicitly call out the `kind:"module"` semantics: *"For `kind:"module"` entries, `count` includes `defines` edges (symbols defined in the file) plus outgoing `imports` and `calls` edges from the file node. For function/method/class entries, `count` is the number of distinct outgoing `calls` edges. Use the entry's `kind` field to interpret the number."*
2. **Update the `file_hubs` section's docstring** with the same explicit decomposition.
3. **Add a unit test on a synthetic small file fixture** that asserts the module-entry `count` matches the known decomposition (3 internal symbols, 2 outgoing calls from one of them, 1 imports edge → expected fan_out = 3 + 2 + 1 = 6 OR whatever the actual semantics produce). The exact assertion locks in the contract; future regressions can't drift silently.
4. **No behavior change** — purely documentation + test gate.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — docstring updates on `wave_graph_report` MCP wrapper.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` (or `test_graph_query.py`) — one synthetic-fixture unit test asserting module fan_out decomposition.

**Out of scope:**

- Changing the underlying `count` semantics. The number is what it is; the doc just explains it.
- Adding per-relation breakouts in the response (`{count: 6, breakout: {defines: 3, calls: 2, imports: 1}}`) — defer until operator demand surfaces.

## Acceptance Criteria

- [x] AC-1: `wave_graph_report` docstring for `fan_out` calls out the module vs function decomposition explicitly.
- [x] AC-2: `file_hubs` section docstring carries the same explanation.
- [x] AC-3: One unit test asserts the exact `count` value for a known small synthetic module fixture, locking in the contract.
- [x] AC-4: All existing tests continue to pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Update wave_graph_report docstring
- [x] Add the synthetic-fixture unit test
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline doc fix |
| AC-2 | required | Parity with the new file_hubs section |
| AC-3 | required | Regression gate against silent semantic drift |
| AC-4 | required | No collateral breakage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Doc + test rather than introducing per-relation breakout | Operator demand is for clarity, not finer-grained counts. A breakout dict adds API surface that 80% of consumers don't need | Surface `count_by_relation: {defines: 3, calls: 2, imports: 1}` (deferred — wait for operator demand) |
| 2026-06-01 | Lock the exact count in a unit test | The semantics are subtle; a future indexer change could shift the count silently. The test makes any shift surface as a failed assertion | Doc-only fix (rejected — relies on future maintainers reading the doc; the test is the contract) |

## Risks

| Risk | Mitigation |
|---|---|
| The locked unit test fails if a legitimate indexer change shifts the count | If the change is intentional, update the assertion + docstring in the same PR; the test is the alarm, not the cage |
| Doc fix lands but operators still hit the confusion when reading via MCP without consulting the docstring | Companion change `02-file-hubs-section-split` removes the conflation at the response shape level — this change is the doc safety net for what remains in `fan_out` |

## Related Work

- Direct response to Solaris field feedback on `1.2.0+312f` (suggestion #5).
- Companion to `02-file-hubs-section-split` — the section split removes the conflation in `chokepoints`; this change clarifies what remains in `fan_out`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
