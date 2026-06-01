# `betweenness_computed` Field on `wave_graph_report` — Distinguish "Empty Section" from "Computation Disabled"

Change ID: `130tw-enh betweenness-computed-field`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-05-31
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

Aceiss field report on `1.1.0+30tt`: `wave_graph_report` returns an empty `betweenness: []` section on graphs above a size threshold. The empty list is correct behavior (NetworkX betweenness centrality is O(VE), prohibitive on large graphs) but indistinguishable from "all nodes have betweenness 0" or "the computation succeeded but no node ranked." Operator can't tell whether to re-run with a smaller subset, skip the section, or report a bug.

Fix: surface an explicit `betweenness_computed: bool` field on the response. When `False`, accompany with `betweenness_skipped_reason: "graph_too_large"` (or similar enum) so the operator knows the section is skipped, not empty.

## Requirements

1. `wave_graph_report_response` adds `betweenness_computed: bool` at the top level. Always present.
2. When betweenness IS computed, `betweenness_computed: true` and `betweenness: [...]` carries the rankings.
3. When betweenness is skipped (graph above size threshold), `betweenness_computed: false`, `betweenness: []`, and `betweenness_skipped_reason: "<short_enum>"` explains why.
4. The size threshold and its rationale are not changed by this change — purely an observability addition.
5. Tests: (a) small graph → `betweenness_computed: true`, list populated; (b) large graph (force the skip path) → `betweenness_computed: false`, `betweenness_skipped_reason` present.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py`: add the two new fields to the response builder. Wrap the betweenness computation site with a try/skip path that sets the fields.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`: 2 regression tests.

**Out of scope:**

- Changing the betweenness skip threshold itself.
- Adding an `enable_betweenness: bool` parameter — the cost model is fixed; user-override would still hit O(VE) and the response budget. If operator demand surfaces, defer to a follow-on.
- Computing approximate betweenness (sampling-based) — significantly larger scope.

## Acceptance Criteria

- [x] AC-1: `wave_graph_report_response` always emits `betweenness_computed: bool`.
- [x] AC-2: When the computation runs, `betweenness_computed: true`. When skipped, `betweenness_computed: false` and `betweenness_skipped_reason: "<enum>"` accompanies.
- [x] AC-3: Enum values are stable strings (`"graph_too_large"` for the size-threshold skip).
- [x] AC-4: 2 regression tests cover computed vs skipped paths.
- [x] AC-5: No other response fields change shape.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `betweenness_computed` / `betweenness_skipped_reason` to the response builder
- [x] Wrap the betweenness path with the skip detection
- [x] Add 2 regression tests
- [x] Run framework tests
- [ ] Close gate (held open across remaining 130tw changes)
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline observability field |
| AC-2 | required | The accompanying skip reason makes the field actionable |
| AC-3 | required | Stable enum so callers can branch |
| AC-4 | required | Regression coverage |
| AC-5 | required | No collateral shape change |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Add observable `betweenness_computed` field rather than user-facing override | The skip is correct behavior on cost grounds; surfacing it directly answers the operator's question without inviting a footgun (manual override that still blows the budget) | Add `force_betweenness: bool` (rejected — invites operator to override a cost-driven skip) |
| 2026-05-31 | Use an enum string for `betweenness_skipped_reason` | Stable string callers can branch on. Free-form text would be less useful programmatically | Numeric code / free-form text (rejected — string enum balances readability and programmatic use) |

## Risks

| Risk | Mitigation |
|---|---|
| Adding a top-level response field could break callers parsing strictly | Field is additive; no removal or rename of existing fields |
| Enum value churn if more skip reasons appear later | The enum is open-ended; future reasons (`"betweenness_disabled_by_config"`, `"missing_dependency"`) layer on without breaking existing callers |

## Related Work

- Same wave: `130tw-enh exclude-external-from-graph-report`, `130tw-enh large-community-pagination`, `130tw-enh fan-in-name-collision-hint-and-seed-note`, `130tw-enh java-receiver-type-resolution`.
- Companion to Change 2 (`130rj-enh graph-tool-shape-consistency`) — same report tool's observability surface.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
