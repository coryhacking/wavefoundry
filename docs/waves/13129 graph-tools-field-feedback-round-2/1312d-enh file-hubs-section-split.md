# Split `file_hubs` Section Out of `chokepoints` on `wave_graph_report`

Change ID: `1312d-enh file-hubs-section-split`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Solaris field report (2026-06-01) on `1.2.0+312f`: `wave_graph_report.chokepoints` shows `StatusBarManager (module)` with `fan_out: 77` at rank #1 alongside JavaScript dashboard functions. The 77 figure is a file-level metric — it counts edges from the file node, which aggregates `defines` + `imports` + nested-symbol attributions. The function-level chokepoints (`GraphPanel` fan_out 125, etc.) carry different semantics — they count direct outgoing `calls` from a single function. Conflating both in one ranking forces operators to do per-entry `kind` inspection to know what the number means.

Fix: split the file-level entries out of `chokepoints` into a dedicated `file_hubs` section. Both views remain available; their semantics are no longer conflated. `chokepoints` becomes a pure function/method/class ranking; `file_hubs` lists the file-level outgoing-edge hubs separately.

## Requirements

1. **Add a new `file_hubs` section to `wave_graph_report`** listing top-N nodes by `fan_out` count where `kind == "module"`. Same entry shape as `chokepoints`: `{node_id, fan_out, label, name_collision_count, same_name_node_count, cross_file_collision}` (using the decomposed fields from the companion change `01-decompose-name-collision-count`).
2. **Filter `kind == "module"` entries out of `chokepoints`** so the section is function/method/class-only.
3. **Same filter for `fan_in` and `fan_out` rankings?** No. Those are usable as combined views — operators reading "top symbols by call-out" generally want both file and function entries. Only `chokepoints` (the explicit "bottleneck risk" framing) needs the split, because that framing assumes function-level call structure.
4. **`file_hubs` participates in the default section set** so operators get architectural orientation across both views without explicit `sections=[...]` request.
5. **Tests** cover (a) `file_hubs` populated with kind=module entries; (b) `chokepoints` no longer contains kind=module entries; (c) entry shape parity with `chokepoints` (same fields except `name_collision_count`/`cross_file_collision` semantics).

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_query.py` — build the `file_hubs` section in `GraphQueryIndex.report()`.
- `.wavefoundry/framework/scripts/server_impl.py` — include `file_hubs` in the default `wanted` section set; apply the same name-collision precompute pass on its entries.
- `.wavefoundry/framework/scripts/tests/test_graph_query.py` + `test_server_tools.py` — regression tests.
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — update the `wave_graph_report` line to mention `file_hubs` alongside `chokepoints` and explain the distinction.

**Out of scope:**

- Filtering modules from `fan_in` / `fan_out` (kept as combined views per Requirement 3).
- A configurable threshold for what counts as a "hub" (file_hubs uses the same chokepoint threshold).

## Acceptance Criteria

- [x] AC-1: `wave_graph_report` response carries a `file_hubs` section as a list of `{node_id, fan_out, label, ...}` entries where every node has `kind: "module"`.
- [x] AC-2: `chokepoints` no longer contains entries where `kind == "module"`.
- [x] AC-3: `file_hubs` is in the default section set (returned without explicit `sections=[...]` request).
- [x] AC-4: Entry shape parity: each `file_hubs` entry has the same field set as a `chokepoints` entry, plus name-collision fields (`same_name_node_count`, `cross_file_collision`).
- [x] AC-5: Operator can request just `file_hubs` via `sections=["file_hubs"]`.
- [x] AC-6: Seed-211 line explains the split AND carries an **explicit chokepoints migration note** — operators who previously read mixed module/function entries from `chokepoints` should know that module entries have moved to `file_hubs`. The note covers both default-section-set consumers (who get both sections automatically) and explicit `sections=["chokepoints"]` consumers (who must add `"file_hubs"` to keep visibility into file-level hubs). (Council action item: reality-checker.)
- [x] AC-7: 3 regression tests; all existing tests pass.
- [x] AC-8: docs-lint passes.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Build `file_hubs` section in `GraphQueryIndex.report()`
- [x] Filter modules from `chokepoints`
- [x] Wire `file_hubs` into default section set in `server_impl.py`
- [x] Apply name-collision precompute to file_hubs entries
- [x] Open `seed_edit_allowed` gate
- [x] Update seed-211 wave_graph_report description
- [x] Run docs-lint
- [x] Close `seed_edit_allowed` gate
- [x] Add 3 regression tests
- [x] Run framework tests
- [x] Close `framework_edit_allowed` gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline new section |
| AC-2 | required | The cleanup of chokepoints to function/method-only — the actual semantic correction |
| AC-3 | required | Discoverability — default-included means operators get the view without learning a new section name |
| AC-4 | required | Shape parity for consistent consumption |
| AC-5 | required | Explicit-request path |
| AC-6 | required | Seed guidance |
| AC-7 | required | Regression coverage |
| AC-8 | required | docs-lint hygiene |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Split `file_hubs` out rather than default-excluding modules from chokepoints | Solaris #1 originally proposed default-exclude. Push-back: file-level fan_out IS legitimate signal — operators asking "which file owns the most outgoing dependencies" want it. Split preserves both views without forcing operator to choose | Default-exclude modules from chokepoints (rejected — drops legitimate signal) |
| 2026-06-01 | Keep `fan_in` / `fan_out` as combined views; only split `chokepoints` | `chokepoints` carries an explicit "bottleneck risk" framing that assumes function-level call structure. fan_in/fan_out are descriptive lists with `kind` field already discriminating. The framing is what's confused, not the listing | Symmetric split on all four sections (rejected — overkill; only chokepoints carries the framing problem) |
| 2026-06-01 | Use same threshold as chokepoints for file_hubs | Avoids tuning surface. If a file has chokepoint-threshold fan_out, it's a hub | Per-section threshold (rejected — extra surface for marginal value) |
| 2026-06-01 | Include `file_hubs` in default section set | Discoverability. Operators learning the new section through use rather than docs | Opt-in only (rejected — operators investigating architectural orientation won't know to ask) |

## Risks

| Risk | Mitigation |
|---|---|
| Existing consumers reading `chokepoints` for "all hubs" lose the module entries silently | Doc the split in the seed; the field semantics are stricter (function-level only) but the listing isn't smaller — file entries are in the new section |
| Operators don't notice `file_hubs` exists | Default-included section + seed-211 update |
| Smaller projects produce empty `file_hubs` because no file crosses the threshold | Empty section is fine; matches existing behavior for empty chokepoints |

## Related Work

- Direct response to Solaris field feedback on `1.2.0+312f` (suggestion #1, modified).
- Companion to `01-decompose-name-collision-count` — file_hubs entries carry the new decomposed collision fields.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
