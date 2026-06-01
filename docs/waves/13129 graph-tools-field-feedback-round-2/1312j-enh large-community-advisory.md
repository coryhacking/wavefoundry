# `large_community_advisory` Diagnostic on `code_graph_community` >200 Nodes

Change ID: `1312j-enh large-community-advisory`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Solaris field report (2026-06-01) on `1.2.0+312f`: the `pagination_hint` shipped in wave 130rj (130tw #4) tells operators *how to page through* a community, but doesn't tell them *not to page* when the community is so large that traversal is the wrong approach entirely. A 3119-member Tests community would take 60+ round-trips to enumerate; the answer the operator usually wants is "use the hub" — `code_callhierarchy` on the community's `hub_node_id` (which `wave_graph_report.communities` already returns).

Fix: emit a structured `large_community_advisory` diagnostic when `total_node_count > 200`. The diagnostic carries `recovery_tools: ["code_callhierarchy", "code_graph_path"]` and a recovery hint pointing at the community's hub. The diagnostic surfaces alongside the existing `pagination_hint` — operators see both "how to page if you must" and "but you probably shouldn't" together.

Plus: add a `community_size_class: "small" | "medium" | "large"` field on the response for quick programmatic branching by callers. Thresholds: <50 small, 50–200 medium, 200+ large.

## Requirements

1. **`community_size_class: str` always present on `code_graph_community` response.** Computed from `total_node_count`: <50 → `"small"`, 50–200 → `"medium"`, 200+ → `"large"`.
2. **When `total_node_count > 200`, emit a `large_community_advisory` diagnostic.** Structured per the framework's `_diagnostic` shape: `{code: "large_community_advisory", message: "<recovery prose>", recovery_tools: ["code_callhierarchy", "code_graph_path"], recovery_usage: "code_callhierarchy(symbol='<hub_node_id>', direction='both')"}`. The hub_node_id is looked up from the community's cluster artifact (same lookup `wave_graph_report.communities` uses).
3. **Recovery message text:** *"Community has {N} members; full traversal will exceed token budgets at default pagination. Consider `code_callhierarchy` on the hub `{hub_node_id}` to identify the community's public API, then narrow with `code_graph_path` between specific endpoints. Pagination remains available via the `pagination_hint` if full enumeration is required."*
4. **Diagnostic surfaces ALONGSIDE the existing `pagination_hint`** — both fields present. The advisory doesn't suppress pagination; it offers an alternative.
5. **Seed-211 update:** add a one-line note explaining the advisory and when to follow it vs page through.
6. **Tests** cover (a) small community → `community_size_class: "small"`, no advisory; (b) medium → `"medium"`, no advisory; (c) large → `"large"` + diagnostic emitted; (d) diagnostic carries the hub_node_id in recovery_usage; (e) advisory and pagination_hint both present on large communities.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — `community_size_class` computation + `large_community_advisory` diagnostic emission in `code_graph_community_response`.
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — interpretation guidance line.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — 5 regression tests.

**Out of scope:**

- Configurable thresholds. <50 / 50–200 / 200+ are fixed at admission; future operator reports may justify making them tunable.
- Auto-fall-through to `code_callhierarchy` on the hub (the advisory is operator-facing guidance, not server-side automation).
- Same shape on `wave_graph_report.communities` entries (operators reading the top-N communities can identify large ones from `node_count`; the per-community advisory triggers when the operator drills in).

## Acceptance Criteria

- [x] AC-1: `code_graph_community` response always carries `community_size_class: "small" | "medium" | "large"`.
- [x] AC-2: `community_size_class` is computed from `total_node_count` per the thresholds: <50 / 50–200 / 200+.
- [x] AC-3: When `total_node_count > 200`, the response's `diagnostics` list contains an entry with `code: "large_community_advisory"`.
- [x] AC-4: The diagnostic's `recovery_usage` references the community's hub_node_id (looked up from the cluster artifact).
- [x] AC-5: The advisory does NOT suppress the existing `pagination_hint` — both fields coexist on large-community responses.
- [x] AC-6: Seed-211 carries a one-line interpretation note.
- [x] AC-7: 5 regression tests cover the trigger matrix; all existing tests pass.
- [x] AC-8: docs-lint passes.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `community_size_class` field + threshold computation
- [x] Add `large_community_advisory` diagnostic emission with hub_node_id lookup
- [x] Open `seed_edit_allowed` gate
- [x] Update seed-211 with the interpretation line
- [x] Run docs-lint
- [x] Close `seed_edit_allowed` gate
- [x] Add 5 regression tests
- [x] Run framework tests
- [x] Close `framework_edit_allowed` gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Always-present field gives callers a stable signal to branch on |
| AC-2 | required | Threshold semantics |
| AC-3 | required | The headline advisory |
| AC-4 | required | Recovery-tool usability — hub_node_id is what the operator needs to act on |
| AC-5 | required | Advisory complements pagination_hint, not replaces it |
| AC-6 | required | Seed guidance |
| AC-7 | required | Regression coverage |
| AC-8 | required | docs-lint hygiene |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Fixed thresholds (<50 / 50–200 / 200+) | Solaris's data point (3119-node community) plus generic token-budget reasoning. Tunable thresholds add surface for marginal benefit at admission | Tunable via parameter (deferred — wait for operator reports asking for it) |
| 2026-06-01 | Advisory + pagination_hint both surface on large communities | The advisory is operator guidance; pagination is the fallback path. Suppressing pagination would be presumptuous — some operators have a legitimate need to enumerate the full community | Suppress pagination_hint on advisory (rejected — removes the fallback path) |
| 2026-06-01 | Look up hub_node_id from the cluster artifact for the recovery_usage | Operator can act on the recovery directly without a follow-up `wave_graph_report` call. The lookup is already used by `wave_graph_report.communities` so the code path exists | Generic recovery message without hub (rejected — actionability lost) |
| 2026-06-01 | Three size classes (small / medium / large) rather than just bool | Programmatic callers benefit from finer signal. Medium communities (50–200) sit in a "fine to page through" zone that's worth distinguishing from small (single-call) | Just `is_large: bool` (rejected — loses the medium tier) |

## Risks

| Risk | Mitigation |
|---|---|
| Operators ignore the advisory and page through anyway | The advisory is guidance, not blocking. The pagination_hint preserves the existing path |
| `hub_node_id` lookup fails (cluster artifact stale) — recovery_usage carries a stale or empty value | Treat lookup failure as "skip the usage field"; the advisory message text remains useful |
| Thresholds prove wrong for some codebase shapes | Operator reports will surface; revisit. Documented as fixed at admission for a reason |

## Related Work

- Direct response to remaining open item from Solaris's evaluation on `1.2.0+312f`.
- Companion to wave 130rj's `130tw-enh large-community-pagination` — that change added the *how to page* hint; this change adds the *consider not paging* nudge.
- Uses the same cluster-artifact lookup as wave 130rj's `130rj-enh graph-tool-shape-consistency` `wave_graph_report.communities` section.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
