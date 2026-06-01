# Fan-In Name-Collision Hint and Seed Note — Surface Simple-Name Attribution Risk on Common Method Names

Change ID: `130tw-enh fan-in-name-collision-hint-and-seed-note`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-05-31
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

Aceiss field report on `1.1.0+30tt`: `wave_graph_report.fan_in` shows entries like `extractor::process` near the top. Investigation reveals the symbol simple-name `process` appears in many distinct classes across the codebase; the call-site scanner resolves bare `something.process(...)` references to whichever `process` symbol matches by simple-name without verifying the receiver class. The same mechanism that produces the false-positive `JSON.writeObject` callers from Change 1 inflates fan_in for any common symbol simple-name.

Two layers of fix:

1. **Observability hint at the report layer**: add a `name_collision_count: int` field on each `fan_in`/`fan_out`/`chokepoints`/`betweenness` entry. The value is the count of distinct nodes in the graph that share the symbol's simple name. When `> 1`, the fan_in figure is potentially over-attributed — the operator sees the risk inline without separate investigation.

2. **Seed-211 note**: add operator guidance explaining how to interpret `name_collision_count > 1` (verify with `code_callhierarchy` on the specific `node_id`; cross-check via `code_definition` to confirm the receiver-type for hot callers).

The receiver-type resolution from Change `130tw-enh java-receiver-type-resolution` addresses the per-call-site filtering at `code_callhierarchy` query time. This change surfaces the *aggregate* risk in the report tool and gives operators the language to interpret it.

## Requirements

1. New helper at report-build time: precompute a simple-name → count map across all graph node_ids. Map key is the symbol simple name (the last `.`-segment after the `::` split); value is the count of distinct nodes that share it.
2. Each `fan_in`, `fan_out`, `chokepoints`, `betweenness` entry carries `name_collision_count: int`. Always present. Value 1 = unique simple name; value > 1 = collision.
3. Computation is O(|nodes|) once per request and adds < 50ms on a 10k-node graph (verified by smoke test or skipped via a documented assertion).
4. Seed-211 receives a new line under the graph-report interpretation guidance: when a top fan_in entry has `name_collision_count > 1`, the count is potentially inflated by simple-name attribution — verify with `code_callhierarchy` on the specific `node_id`.
5. Tests: (a) unique-name entry → `name_collision_count: 1`; (b) collision entry → `name_collision_count: N > 1`; (c) field present on all four sections (fan_in, fan_out, chokepoints, betweenness).

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py`: precompute simple-name → count map; attach `name_collision_count` to entries.
- `.wavefoundry/framework/seeds/211-guru.prompt.md`: add the interpretation guidance line.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`: 3 regression tests covering the field presence and value.

**Out of scope:**

- Auto-deduplication or auto-suppression of high-collision entries from the report — observability only.
- Receiver-type resolution at the graph-build layer (would deduplicate the source of the collision but is significantly larger scope; Change 1 addresses the per-query layer).
- Backporting the field to `code_graph_community`'s member entries (defer; operator-validation-driven).

## Acceptance Criteria

- [x] AC-1: A simple-name → count map is computed once per `wave_graph_report` call.
- [x] AC-2: Each `fan_in`, `fan_out`, `chokepoints`, `betweenness` entry carries `name_collision_count: int`.
- [x] AC-3: Value reflects the count of distinct nodes sharing the symbol's simple name.
- [x] AC-4: Seed-211 carries an interpretation note for the field.
- [x] AC-5: 3 regression tests cover field presence and value.
- [x] AC-6: docs-lint passes after seed edit.
- [x] AC-7: All existing tests continue to pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Implement simple-name → count helper + attach to report entries
- [x] Open `seed_edit_allowed` gate
- [x] Add seed-211 interpretation guidance line
- [x] Run docs-lint
- [x] Close `seed_edit_allowed` gate
- [x] Add 3 regression tests
- [x] Run framework tests
- [ ] Close `framework_edit_allowed` gate (held open across remaining 130tw changes)
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The precompute is the foundation |
| AC-2 | required | The headline observability field |
| AC-3 | required | The field's semantic meaning |
| AC-4 | required | Operator interpretation guidance |
| AC-5 | required | Regression coverage |
| AC-6 | required | docs-lint hygiene |
| AC-7 | required | No regressions |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Observability + seed note rather than auto-suppression | Suppressing high-collision entries silently would hide legitimately-important common-name symbols (e.g. an interface method genuinely called from 50 classes). Operator-facing surface lets the human judge | Auto-suppress entries above a threshold (rejected — false-positive on legitimate common-name hot symbols) |
| 2026-05-31 | Compute the map per-request, not at index time | Avoids index-shape changes and version bumps. The compute is O(|nodes|) once per request — well under the response budget on realistic graphs | Cache in the indexer (deferred — index bump cost not justified for this signal) |
| 2026-05-31 | Pair the field with the seed note in one change | The field without operator guidance is just more JSON; the guidance without the field is unactionable. Bundling them keeps the audit trail tight | Two changes (rejected — they're useless apart) |
| 2026-05-31 | Use simple-name (last `.`-segment of the symbol part after `::`) as the collision key | Matches the receiver-type-conflation pattern from Change 1; consistent with how the call-site scanner currently attributes by simple name | Full qualified name (rejected — wouldn't collide; not the right signal) |

## Risks

| Risk | Mitigation |
|---|---|
| O(|nodes|) precompute increases response latency on very large graphs | Measure during implementation; single pass over node_ids is fast (< 50ms at 10k nodes). If profiling shows a problem, cache in the index — but defer the index bump until necessary |
| Operators interpret `name_collision_count > 1` as "this is wrong" rather than "this is potentially over-attributed" | Seed-211 wording uses "potentially inflated" / "verify with code_callhierarchy" — soft language that invites verification, not dismissal |
| Field is always present (including value 1), inflating response size | Trivial — one integer per entry across at most ~40 entries per report (top-N across 4 sections × ~10 each). Negligible |

## Related Work

- Surfaces the *aggregate* risk that Change `130tw-enh java-receiver-type-resolution` filters at *per-query* time. Pair the changes in the wave council reading.
- Same wave: `130tw-enh exclude-external-from-graph-report`, `130tw-enh betweenness-computed-field`, `130tw-enh large-community-pagination`, `130tw-enh java-receiver-type-resolution`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
