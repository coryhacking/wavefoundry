# Graph Tool Response Shape — Community ID Dual Return, Pagination, Per-Hop Attribution, Community Overview

Change ID: `130rj-enh graph-tool-shape-consistency`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

Aceiss field feedback §1.1, §1.3, §2.2, §2.4 identified four response-shape inconsistencies in the graph tools that cause unnecessary round-trips and missing signals:

- **§1.1 Community label ≠ community ID.** `code_callhierarchy` and `code_impact` return `"community": "AuthorizationContext"` (label). `code_graph_community` requires `project:c16` (numeric ID). Every drill-in requires a failed call to recover the ID from the suggestions list.
- **§1.3 No pagination on `code_graph_community`.** Communities of 80+ nodes blow agent context limits. No `limit`/`offset`.
- **§2.2 No community overview in `wave_graph_report`.** Architectural orientation requires per-community discovery calls; should be a single section.
- **§2.4 No per-hop attribution on `code_impact`.** Direct callers (hop=1) vs transitive (hop>1) carry different risk implications. Currently a flat list.

All four are small, self-contained API improvements with no breaking changes (additive fields + new optional params).

## Requirements

1. Every tool that surfaces a `community: "<label>"` field also surfaces `community_id: "project:cN"` alongside. Affected tools: `code_callhierarchy` (outgoing entries, incoming entries, context entries), `code_impact` (affected entries). Implemented via a new `_load_cluster_lookup_with_ids` helper that returns `node_id → (label, community_id)` tuples; existing `_load_cluster_lookup` retained for backward compatibility with future call sites that only need the label.
2. `code_graph_community` accepts `limit: int = 50` and `offset: int = 0` parameters (max `limit=500`). Response carries `total_node_count`, `returned_count`, `offset`, `has_more`. The legacy `node_count` field is retained but now equals `returned_count` (not the total) to preserve old callers' shape — total is in the new `total_node_count` field.
3. `code_impact` (graph mode) adds `hop: N` to each `affected` entry where N is the minimum hop count from the queried symbol to the affected node along `imports`/`calls` reverse edges. Implementation: replace `graph_impact`'s use of `self.traverse(...)` with a direct BFS that records per-node depth, since the existing `traverse` returns visited-set + edges without depth.
4. `wave_graph_report` gains a `communities` section listing top communities by `node_count` with `community_id`, `label`, `node_count`, `hub_node_id`, `hub_label` (top-degree member). Section is included in the default section set so callers get it without opt-in. Limit is shared with the existing `limit` parameter.
5. No existing test fails. Where existing tests assert response shape (e.g. snapshot tests on `code_callhierarchy.outgoing` rows), the new `community_id: null`/`hop: N` fields appear and tests update minimally.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py`:
  - `_load_cluster_lookup_with_ids` (new helper).
  - `code_callhierarchy_response` `_node_entry` + context block: attach `community` + `community_id`.
  - `code_impact_response` graph mode: use `_load_cluster_lookup_with_ids` and surface `community_id` on each `affected` entry.
  - `code_graph_community_response`: `limit`/`offset` params + `total_node_count`/`returned_count`/`offset`/`has_more` response fields.
  - `wave_graph_report_response`: gain `communities` section.
  - MCP wrappers for `code_graph_community` updated to expose the new params.
- `.wavefoundry/framework/scripts/graph_query.py`:
  - `graph_impact` rewritten to track per-node hop distance via local BFS; each `affected` entry gains `hop: N`.
- Tests in `.wavefoundry/framework/scripts/tests/test_server_tools.py`:
  - Add coverage for `community_id` presence on `code_callhierarchy.outgoing`/`incoming`/`code_impact.affected`.
  - Add coverage for `code_graph_community` pagination (limit, offset, has_more, total_node_count).
  - Add coverage for `code_impact.affected[].hop` field.
  - Add coverage for `wave_graph_report.communities` section presence.
  - Update any existing snapshot/equality tests that assert response shape so the new fields don't break them.

**Out of scope:**

- Backward-incompatible removal of `node_count` from `code_graph_community` response. Retained as alias for `returned_count`.
- Case-insensitive label-accepting in `code_graph_community` (Aceiss §1.1 suggestion). The dual-return fix removes the need for the label-as-input path; label-by-label resolution is deferred.
- `betweenness` section interaction with the new `communities` section (covered by `130rj-enh generated-code-classifier-and-filters`).

## Acceptance Criteria

- [x] AC-1: `_load_cluster_lookup_with_ids` returns `dict[str, tuple[str, str]]` keyed by node_id, with `(label, community_id)` values. Returns `{}` when the cluster artifact is absent.
- [x] AC-2: `code_callhierarchy_response` attaches `community` and `community_id` to every entry in `outgoing`, `incoming`, and `context` (when `context_depth > 0`). Unresolved nodes get `community_id: null`.
- [x] AC-3: `code_impact_response` (graph mode) attaches `community` and `community_id` to every entry in `affected`.
- [x] AC-4: `code_graph_community_response` accepts `limit` (default 50, clamped to 1..500) and `offset` (default 0, clamped to 0+). Response carries `total_node_count`, `returned_count`, `offset`, `has_more`, and the legacy `node_count` (= `returned_count`) for back-compat.
- [x] AC-5: `graph_impact` records per-node minimum hop distance via local BFS and emits `hop: N` on each `affected` entry. Direct callers carry `hop: 1`; nodes reachable only at max_hops carry `hop: max_hops`.
- [x] AC-6: `wave_graph_report_response` gains a `communities` section listing top communities by `node_count` (limited by the existing `limit` param). Each entry carries `community_id`, `label`, `node_count`, `hub_node_id`, `hub_label`. Section is in the default-included section set so callers receive it without opt-in.
- [x] AC-7: New tests in `test_server_tools.py` cover each of the above response-shape additions.
- [x] AC-8: All existing framework tests continue to pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `_load_cluster_lookup_with_ids` helper
- [x] Update `code_callhierarchy_response` to surface `community_id` (outgoing + incoming + context)
- [x] Update `code_impact_response` to use `_load_cluster_lookup_with_ids` and surface `community_id`
- [x] Rewrite `graph_impact` BFS to track per-node hop distance and emit `hop` on each `affected` entry
- [x] Add `limit`/`offset` params + `total_node_count`/`has_more` to `code_graph_community_response`
- [x] Update MCP wrapper `code_graph_community` to expose `limit`/`offset`
- [x] Add `communities` section to `wave_graph_report_response` with `community_id`/`label`/`node_count`/`hub_*`
- [x] Add regression tests in `test_server_tools.py`
- [x] Run framework tests; fix any existing-shape assertions that need updating
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Foundational helper used by AC-2 and AC-3 |
| AC-2 | required | The Aceiss §1.1 fix at the most-used drill-in source (`code_callhierarchy`) |
| AC-3 | required | Same fix at the second-most-used drill-in source (`code_impact`) |
| AC-4 | required | The Aceiss §1.3 pagination fix; without it communities of 80+ are unusable |
| AC-5 | required | The Aceiss §2.4 per-hop attribution fix; informs blast-radius severity |
| AC-6 | required | The Aceiss §2.2 community-overview section; eliminates per-community discovery dance |
| AC-7 | required | Regression coverage for each new field/parameter |
| AC-8 | required | No existing tests regress |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Dual-return (`community` + `community_id`) instead of case-insensitive label-as-input | Both approaches fix the failed-call dance, but dual-return is additive and stateless. Case-insensitive label-input would require disambiguation logic when multiple communities share label prefixes, and still doesn't help callers who serialize the response without knowing they need the ID | Case-insensitive label input on `code_graph_community` (deferred — additive `community_id` covers the use case; label-as-input adds parsing surface) |
| 2026-05-31 | Keep legacy `node_count` as alias for `returned_count` | Existing dashboard JS / external consumers read `node_count`; renaming would break them. Adding `total_node_count` as a new field and aliasing `node_count` to `returned_count` preserves both shapes | Rename `node_count` to `total_node_count` and require callers to update (rejected — breaking change) |
| 2026-05-31 | New local BFS in `graph_impact` rather than extending `traverse` | `traverse` is a shared utility; adding a depth return value affects every caller and risks subtle bugs. A local BFS in `graph_impact` is ~20 LOC, isolated, and matches the existing dedupe semantics (edge-key set) without disturbing `code_callhierarchy` / `code_callgraph` / `code_graph_path` | Extend `traverse` to return per-node depths (rejected — wider blast radius for a single-caller need) |
| 2026-05-31 | `communities` section in the default set rather than opt-in | The Aceiss §2.2 friction is "I have to make a separate call to discover communities." Putting the section behind an opt-in `sections=["communities"]` keeps the same friction for callers using the default. The section is bounded by the existing `limit` param so output stays small | Opt-in only (rejected — preserves the original friction; defeats the point of the change) |
| 2026-05-31 | Pagination default `limit=50` | Matches Aceiss §1.3 ("communities of 248 nodes return ~90,000 characters and hit inline token limits"). A 50-member page keeps output under ~10K tokens for typical node payloads | Default `limit=100` (rejected — too many for typical context; degenerate cases blow limits). Default `limit=20` (rejected — paginates too aggressively for normal-size communities) |

## Risks

| Risk | Mitigation |
|---|---|
| Existing tests that snapshot the full response shape break when new fields appear | New fields are additive (`community_id`, `hop`, `total_node_count`, etc.); existing assertions on individual fields don't care about extras. Snapshot tests update minimally |
| The `community_id` field on `code_callhierarchy.context` entries is a small response-size increase | Negligible — one short string per entry; the alternative (continued failed-call recovery) is worse |
| `graph_impact` BFS rewrite could subtly change the affected set if the dedupe semantics differ | Dedupe by edge-key tuple matches `traverse`'s seen_edges set; affected set is the visited node set minus the start (same as before). The only new behavior is the per-node depth recording |
| `wave_graph_report.communities` section adds a cluster-artifact-load cost on every report call | Load is cheap (`_load_script` is memoized; `read_cluster_payload` reads one JSON file); fails open (empty list) on errors |
| Pagination changes the response for callers who were relying on the legacy "all-nodes" behavior | Legacy `node_count` retained as alias; callers reading just `nodes` get the first 50 by default (rather than all). Net positive for context limits; callers wanting all-nodes pass `limit=500` |

## Related Work

- Wave 130rj sibling changes: `130rj-enh seeds-pattern-library-and-recipes` (seed updates that reference these shape changes), `130rj-enh code-ask-fast-mode`, `130rj-enh generated-code-classifier-and-filters`, `130rj-enh aop-advice-empty-incoming-detection`.
- Builds on wave 130et / 130ol / 130qf (graph extractor foundation).

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
