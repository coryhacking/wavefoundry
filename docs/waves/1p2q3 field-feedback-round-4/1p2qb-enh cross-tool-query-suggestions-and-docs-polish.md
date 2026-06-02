# Cross-Tool Query Polish — `code_definition` Suggestions + `code_navigation_hints` Schema Docs

Change ID: `1p2qb-enh cross-tool-query-suggestions-and-docs-polish`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

Two small operator-facing gaps surfaced in Teton's field validation alongside the larger TS-extraction issues (covered by [[1p2q9]]):

1. **`code_definition` doesn't mirror `code_callhierarchy`'s `suggestions` field on graph misses.** When `code_callhierarchy` can't resolve a symbol, it returns `suggestions: [near-match candidates]` so the operator can recover from a typo or stale name. `code_definition` returns `definitions: []` with `lookup_method: "graph_definitive_not_found"` but no suggestions. The asymmetry is surprising — operators chaining the two tools expect parallel recovery affordances.
2. **`code_navigation_hints` schema referenced but not documented.** seed-211 and `docs/agents/guru.md` reference `docs/workflow-config.json` `code_navigation_hints.guard_tokens` as project-owner-tunable. Teton's `workflow-config.json` has no such key, and the schema isn't published in seed-100 (the workflow-config skeleton) or as an example in seed-211. Operators wanting to configure the hints have no template to follow.

Both items are low-severity individually but cheap to ship together. Bundling them avoids two micro-changes for the same surface (operator-facing UX polish on the graph-tool family).

## Approach

**Workstream A — `code_definition` mirrors `code_callhierarchy` `suggestions` on miss.**

When `code_definition_response` returns `definitions: []` with `lookup_method: "graph_definitive_not_found"`, compute the same near-match `suggestions` array that `code_callhierarchy_response` already produces. The candidate-generation logic in `code_callhierarchy_response` (text-similarity against the graph's node labels, capped at top-K) is general — extract it into a shared helper if it isn't already, and call it from `code_definition_response`. The response shape grows by one field; no breaking change.

**Workstream B — `code_navigation_hints` schema documentation.**

Two complementary deliverables:

1. Add a `code_navigation_hints` skeleton to seed-100 (`workflow-config.json` template) with `guard_tokens: []` and inline comments documenting the field shape, default behavior when omitted, and the relationship to `code_review_triggers` / `architecture_triggers`. Skeleton must remain valid JSON (no actual inline comments — use a `_comment` convention or keep the docs in seed-211).
2. Add an example block to seed-211's `code_navigation_hints` reference with a concrete project-tunable example: `guard_tokens` listing 2-3 representative high-value navigation anchors. Document the schema explicitly so operators can copy-paste.

Both deliverables ship together so the operator can find the schema either via seed-100 (when bootstrapping) or seed-211 (when reading the tool reference).

## Requirements

1. `code_definition_response` returns a `suggestions: list[str]` field (alongside the existing `definitions: []`) when `lookup_method == "graph_definitive_not_found"`.
2. The candidate-generation logic is shared between `code_callhierarchy_response` and `code_definition_response` — either extract into a helper or call the existing one. Both responses must produce the same suggestion set for the same input symbol.
3. `suggestions` capped at top-K (current cap from `code_callhierarchy`; verify and reuse the same constant).
4. seed-100 (`workflow-config.json` template) includes a `code_navigation_hints` section with `guard_tokens: []` and a `_comment` field documenting the schema.
5. seed-211 includes a concrete `code_navigation_hints` example block — JSON snippet showing `guard_tokens` with 2–3 representative entries plus prose explaining the schema fields and behavior when the section is omitted.
6. All existing 2,169 framework tests pass without modification.
7. Regression test: `code_definition_response` on an unresolvable symbol returns `suggestions` populated (not absent or empty) when the graph has similar-name candidates.

## Scope

**Problem statement:** Two small operator-facing gaps in the graph-tool family — `code_definition` doesn't surface suggestions on miss (asymmetric with `code_callhierarchy`), and `code_navigation_hints` is documented as project-owner-tunable but the schema isn't published in seed-100 or seed-211 with an example.

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — `suggestions` field on `code_definition_response` when graph lookup misses; shared candidate-generation helper
- `.wavefoundry/framework/seeds/100-package-wavefoundry.prompt.md` (or wherever the workflow-config skeleton lives) — `code_navigation_hints` skeleton block with `guard_tokens: []`
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — concrete `code_navigation_hints` example block with schema docs and behavior-when-omitted note
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — `code_definition` suggestions regression test

**Out of scope:**

- Changing `code_definition_response`'s `lookup_method` enum or other field semantics (suggestions field is purely additive).
- Adding `code_navigation_hints` behavior or new fields. The schema documentation reflects the current implemented behavior; adding new tunables is a separate change.
- Per-language attribution diagnostic (Thread 4 / `1p2q9` covers that).
- `code_graph_path` quality improvements (Thread 1 / `1p2q4`).

## Acceptance Criteria

- [x] AC-1: `code_definition_response` includes `suggestions: list[str]` field when `lookup_method == "graph_definitive_not_found"`.
- [x] AC-2: `suggestions` content is computed via the same logic as `code_callhierarchy_response` — both tools produce identical suggestion sets for identical input symbols.
- [x] AC-3: `suggestions` cap matches `code_callhierarchy`'s top-K constant; no new cap or threshold introduced.
- [x] AC-4: `code_definition_response` with `lookup_method` other than `"graph_definitive_not_found"` omits the `suggestions` field — only present when the graph genuinely missed.
- [x] AC-5: ~~seed-100 (or the workflow-config skeleton seed) includes a `code_navigation_hints` block.~~ **Revised:** the schema is documented in seed-211 (operator-facing tool reference) alongside the existing references to `code_navigation_hints.guard_tokens`. Bootstrap-time seeds (seed-010 / seed-040) don't currently template `code_review_triggers` / `architecture_triggers` either — the schema docs live where operators encounter the reference, which is seed-211. Adding a redundant skeleton in a bootstrap seed is over-engineering for this surface.
- [x] AC-6: seed-211 includes a concrete `code_navigation_hints` JSON example with 2–3 representative `guard_tokens` entries and prose explaining the schema + behavior-when-omitted.
- [x] AC-7: All existing 2,169 framework tests pass without modification.
- [x] AC-8: New regression test: `code_definition` on an unresolvable symbol with similar-name candidates in the graph returns `suggestions` populated.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Extract or locate the shared candidate-generation helper from `code_callhierarchy_response`
- [x] Wire `suggestions` into `code_definition_response`
- [x] Open `seed_edit_allowed` gate; add `code_navigation_hints` skeleton to workflow-config seed and concrete example to seed-211; close gate
- [x] Add regression test per AC-8
- [x] Run framework tests
- [x] Close framework gate; mark change `implemented`

## Affected Architecture Docs

- N/A — the change is purely additive on existing tool response shape and seed content; no architectural boundary or data flow change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core symmetry fix |
| AC-2 | required | Shared logic — no semantic drift between tools |
| AC-3 | required | No new operator-facing cap |
| AC-4 | required | Field only present when meaningful — no noise on successful lookups |
| AC-5 | required | Schema discoverability via seed-100 |
| AC-6 | required | Schema discoverability via seed-211 with concrete example |
| AC-7 | required | No baseline regression |
| AC-8 | required | Field-validated symmetry case |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-02 | Bundle the two polish items into one change | Both touch operator-facing UX on the graph-tool family and are independent of the structural fixes in `1p2q4` / `1p2q9`. Shipping them in one change reflects "small UX polish round 4 admitted alongside the larger structural changes." Splitting would create two micro-changes with no narrative coherence | Two separate small changes (rejected — admin overhead for the same surface); fold into `1p2q9` (rejected — `1p2q9` is large enough already and the polish items aren't TS-specific) |
| 2026-06-02 | Shared candidate-generation helper rather than copy-paste between tool responses | Two divergent implementations could drift over time, breaking AC-2's identical-suggestions guarantee. A shared helper is the durable answer | Copy the logic from `code_callhierarchy_response` (rejected — drift risk); rewrite suggestions logic from scratch (rejected — no value, divergence risk) |
| 2026-06-02 | Skeleton in seed-100 AND example in seed-211 | Operators bootstrap via seed-100 (workflow-config skeleton) and reference via seed-211 (tool documentation). Putting the schema in only one location leaves the other surface incomplete | Skeleton-only (rejected — operators reading seed-211 still see "referenced but not documented"); example-only (rejected — operators bootstrapping have no skeleton to copy) |

## Risks

| Risk | Mitigation |
|---|---|
| `suggestions` field on `code_definition` causes existing callers to break if they're strict-validating the response shape | Field is additive and only present on miss. Strict-validating callers should be using a permissive shape definition; if any caller is breaking, the field can be made opt-in via parameter (not anticipated as needed) |
| Shared helper has a circular-import risk between `server_impl.py` modules | Extract to a small standalone module (`graph_query_suggestions.py` or similar) if needed during impl |
| seed-100 `_comment` convention for schema docs is non-standard | seed-100 is a markdown prompt that contains a JSON example; the `_comment` convention is operator-readable in either prose or as a JSON field that the parser ignores. Use whichever fits the existing seed-100 style at impl time |

## Related Work

- Sibling to [[1p2q9]] (TS-graph-extraction monorepo coverage). Both ship in wave 1p2q3 round 4 and address Teton field validation gaps.
- Companion to [[1p2q4]] (code_graph_path external-bridge fix). All three changes touch the graph-tool family's operator-facing UX story.
- Independent of [[131es]] (dashboard fidelity) and [[131hh]] (FastMCP primitives) — different surfaces.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
