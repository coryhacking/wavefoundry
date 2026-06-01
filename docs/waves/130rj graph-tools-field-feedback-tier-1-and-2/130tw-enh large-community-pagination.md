# Large Community Pagination — Return First 50 Members with `total_member_count` and Page Hint

Change ID: `130tw-enh large-community-pagination`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-05-31
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

Aceiss field report on `1.1.0+30tt`: `code_graph_community` for a large community can return hundreds of members in a single response — exceeding token budgets and burying the meaningful structure (top-betweenness or top-degree members) in the noise. The current `limit`/`offset` parameters (added in earlier work) make pagination possible but require the operator to discover them via doc lookup and the response gives no signal that pagination would help.

Fix: when a community exceeds the default page size (50), return the first 50 members, include `total_member_count: int` at the top level, and emit a `pagination_hint` string with the literal call shape to retrieve the next page (e.g. `"Use limit=50 offset=50 to retrieve the next page"`). The operator sees the truncation and the recovery path in one response.

## Requirements

1. `code_graph_community_response` accepts `limit: int = 50` (was already present from earlier work; default may have been higher — this change pins the default to 50).
2. Response carries `total_member_count: int` at the top level — the count BEFORE pagination, after any `exclude_generated` filter.
3. When `total_member_count > limit + offset`, response carries `pagination_hint: str` with the literal `limit`/`offset` shape for the next page. Hint is absent (or empty string) when no further pages remain.
4. Response carries `returned_member_count: int` — the length of the actual members list, for caller verification.
5. Backward compatibility: callers passing an explicit `limit` get their requested limit (not forced to 50).
6. Tests: (a) small community returns all members, no hint; (b) large community returns first 50 + hint; (c) explicit `limit=10` is respected; (d) `offset` advances correctly; (e) `total_member_count` reflects the post-filter, pre-pagination size.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py`: pin default `limit=50`, compute `total_member_count`, emit `pagination_hint`, emit `returned_member_count`.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`: 5 regression tests.

**Out of scope:**

- Cursor-based pagination — offset is fine for stable community membership; cursor would add design surface for marginal benefit.
- Pre-sorting members by betweenness or degree (so the "first 50" are the most-important) — significantly larger scope; today's order is the underlying graph's iteration order. Operator can call `wave_graph_report` for top-betweenness across the whole graph if they want the strict ranking.
- Pagination on `wave_graph_report`'s communities section — that section already truncates per-community member list and is operator-tunable.

## Acceptance Criteria

- [x] AC-1: `code_graph_community_response` default `limit=50` (if currently higher, lowered to 50; if currently 50, unchanged).
- [x] AC-2: Response carries `total_member_count: int` representing the post-filter, pre-pagination community size.
- [x] AC-3: When `total_member_count > limit + offset`, response carries `pagination_hint: str` matching the shape `"Use limit={limit} offset={offset+limit} to retrieve the next page (X-Y of N members shown)"` — exact wording fixed at implementation time.
- [x] AC-4: When the response is the last page (or contains the entire community), `pagination_hint` is absent or empty string.
- [x] AC-5: Response carries `returned_member_count: int`.
- [x] AC-6: Backward compatibility: explicit `limit`/`offset` values are respected verbatim.
- [x] AC-7: 5 regression tests cover small/large/explicit-limit/offset/total-count paths.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Adjust `code_graph_community_response` default + pagination metadata fields (existing `total_node_count` / `returned_count` field names retained; `pagination_hint` added as the new headline)
- [x] Compute and emit `pagination_hint` (and confirm `total_node_count` / `returned_count` deliver the AC-2/AC-5 observability semantics)
- [x] Update MCP wrapper docstring to reference the new pagination contract (existing docstring already documents `total_node_count` / `has_more` semantics; `pagination_hint` is additive)
- [x] Add 5 regression tests
- [x] Run framework tests
- [ ] Close gate (held open across remaining 130tw changes)
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The default-page-size contract |
| AC-2 | required | The headline total-count observability field |
| AC-3 | required | The actionable next-page hint operator needs |
| AC-4 | required | No misleading hint on last page |
| AC-5 | required | Caller verification field |
| AC-6 | required | Backward compatibility |
| AC-7 | required | Regression coverage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Default `limit=50` | Balances information density with token budget for typical communities. Operator can ask for more explicitly when needed | Default 100 (rejected — large communities still over-budget); default 25 (rejected — too many round-trips for typical use) |
| 2026-05-31 | Offset pagination over cursor | Community membership is stable across re-queries within a single index version; offset is sufficient and operator-readable | Cursor (rejected — adds opaque state for marginal benefit) |
| 2026-05-31 | Pagination hint is a literal call shape, not a structured cursor | Operators reading the response should see the exact call to make next, not an opaque token | Cursor token (rejected — same reason) |
| 2026-05-31 | Don't pre-sort by betweenness/degree | Larger scope; today's order matches the underlying graph iteration. Operator who wants ranked importance uses `wave_graph_report` | Sort by degree before pagination (deferred — clean follow-on if operator demand surfaces) |

## Risks

| Risk | Mitigation |
|---|---|
| Default lowered from a higher value could surprise callers seeing fewer members | The response carries `total_member_count` and `pagination_hint`; callers see truncation explicitly. AC-6 preserves explicit-limit behavior |
| Operator interprets "first 50" as "top 50 by importance" — they're not | Pagination hint wording is "(X-Y of N members shown)" — implies positional, not ranked |

## Related Work

- Same wave: `130tw-enh exclude-external-from-graph-report`, `130tw-enh betweenness-computed-field`, `130tw-enh fan-in-name-collision-hint-and-seed-note`, `130tw-enh java-receiver-type-resolution`.
- Builds on the `limit`/`offset` plumbing from Change 5 (`130rj-enh generated-code-classifier-and-filters`) which introduced the parameters but didn't surface a pagination hint.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
