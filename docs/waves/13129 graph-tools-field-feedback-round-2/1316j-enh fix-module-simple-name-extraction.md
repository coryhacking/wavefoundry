# Fix Module-Node `same_name_node_count` — Extract Basename, Not Extension

Change ID: `1316j-enh fix-module-simple-name-extraction`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Solaris round-trip report on `1.2.1+315o` (2026-06-01): every Swift module entry in `file_hubs` reports `same_name_node_count: 72` — the identical value for every entry. Reproducer:

```
"file_hubs": [
  {"label": "StatusBarManager",  "kind": "module", "same_name_node_count": 72, ...},
  {"label": "PresetsEditorView", "kind": "module", "same_name_node_count": 72, ...},
  {"label": "LightingRoutines",  "kind": "module", "same_name_node_count": 72, ...}
]
```

72 happens to be the total number of Swift module nodes in Solaris's graph. Ground-truth verification via `code_keyword(query="StatusBarManager", glob="**/*.swift")` shows 8 occurrences total — nowhere near 72.

Root cause: the simple-name extraction in `_collision_fields` and the precompute loops in `server_impl.py:wave_graph_report_response` does:

```python
symbol = nid.rsplit("::", 1)[-1] if "::" in nid else nid
simple = symbol.rsplit(".", 1)[-1]
```

For symbol nodes (`path/Foo.java::Foo.bar`), `simple = "bar"` ✓.
For module nodes (`SolarisMonitor/Sources/StatusBarManager.swift`), there is no `::`, so `symbol = nid` (full path), and `simple = "swift"` (the file extension!). Every Swift module entry shares simple-name "swift", and the count is the total Swift module count (72 in Solaris's case).

The bug existed in wave 130rj's `name_collision_count` too, but didn't surface because `chokepoints` previously mixed module entries — and the bug just produced a high constant that operators might dismiss as "many same-named modules" without verifying. Wave 13129 surfaced it cleanly because:
- `file_hubs` (1312d) made module entries first-class
- `same_name_node_count` (1312b) gave the bug a memorable name

The fix is small: for module/file nodes (no `::`), extract the basename without extension as the simple name. `SolarisMonitor/Sources/StatusBarManager.swift` → simple name `"StatusBarManager"`.

## Requirements

1. **New helper `_node_simple_name(nid: str) -> str`** in `server_impl.py` that:
   - For node ids with `::`: returns the last `.`-segment of the symbol portion (current behavior).
   - For node ids without `::` (module/file nodes): returns the file basename without extension.
   - Returns empty string when the id is empty or yields no simple name.
2. **All three precompute loops** in `wave_graph_report_response` consume the helper:
   - `project_files_by_simple_name` builder
   - `external_counts_by_simple_name` builder
   - `project_node_count_by_simple_name` builder
3. **`_collision_fields` uses the helper** for its own extraction.
4. **Tests** cover:
   - Module entry simple name extraction: `path/StatusBarManager.swift` → `"StatusBarManager"`
   - Symbol entry preserved: `path/JSON.java::JSON.writeObject` → `"writeObject"`
   - Module + class collision: two module nodes with the same basename produce `same_name_node_count: 2`
   - Distinct module nodes (different basenames) produce distinct collision counts (regression guard for the 72-on-every-module symptom)
5. **The fix MUST preserve correct behavior for the existing wave-13129 test fixtures** — verified by all existing receiver-type / file-hubs / collision-count tests passing.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — `_node_simple_name` helper + three precompute loops + `_collision_fields` consumer.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — 4 regression tests.

**Out of scope:**

- Persisting simple-name in the index. Compute at request time only (consistent with the existing 1312b architecture).
- Backporting to the deprecated `name_collision_count` alias semantics — the alias maps to `same_name_node_count`, so the fix flows through automatically.
- Changing `cross_file_collision` semantics — when two distinct module nodes share the same basename (e.g., `mod_a/Foo.swift` + `mod_b/Foo.swift`), they're in different source files, so `cross_file_collision: true`. This is correct.

## Acceptance Criteria

- [x] AC-1: `_node_simple_name` helper exists and returns the basename-without-extension for module/file nodes (no `::`) and the last-`.`-segment for symbol nodes (`::`-containing).
- [x] AC-2: All three precompute loops in `wave_graph_report_response` use the helper consistently.
- [x] AC-3: `_collision_fields` uses the helper for input extraction.
- [x] AC-4: A module entry like `path/StatusBarManager.swift` reports `same_name_node_count: <count of StatusBarManager nodes including class twin>` — never the total module count.
- [x] AC-5: Distinct module nodes with distinct basenames report distinct collision counts (regression guard).
- [x] AC-6: Symbol entries continue to report correct counts (regression guard for the existing wave-13129 tests).
- [x] AC-7: 4 new regression tests cover the matrix; all 2032 existing tests pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `_node_simple_name` helper
- [x] Rewrite the three precompute loops to use the helper
- [x] Update `_collision_fields` to use the helper
- [x] Add 4 regression tests
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The helper is the single source of truth for simple-name semantics |
| AC-2 | required | All consumers must use the same simple-name definition |
| AC-3 | required | The downstream consumer |
| AC-4 | required | The Solaris-reported symptom — module count must be the real per-symbol count |
| AC-5 | required | Regression guard for the "constant across all entries" failure mode |
| AC-6 | required | No regression on symbol entries |
| AC-7 | required | Regression coverage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Extract basename without extension for module nodes | `path/StatusBarManager.swift` → `"StatusBarManager"` matches what operators would consider the "simple name" of the file. Aligns with how class nodes' simple-name extraction works (last `.`-segment of qname) | Use full path as simple name (rejected — would never collide with class nodes' simple name); use file extension as simple name (current behavior — produces the 72 bug) |
| 2026-06-01 | Single helper consumed by all three loops + collision-fields | The bug existed because three loops independently extracted simple names with the same broken logic. A single helper makes future drift impossible | Inline-fix each loop (rejected — perpetuates the duplication; another similar bug could surface in a different consumer) |
| 2026-06-01 | Compute at request time, not index time | Consistent with the existing 1312b architecture. The bug fix doesn't require an index version bump | Persist in graph artifact (rejected — bump cost not justified for this fix) |
| 2026-06-01 | Land in wave 13129 as a follow-on rather than a new wave | The bug is a direct consequence of wave 13129's surface changes (file_hubs + decomposed collision count). Closing the loop in the same wave preserves audit-trail coherence | Open a new wave (rejected — scope is too small and tightly coupled to 13129) |

## Risks

| Risk | Mitigation |
|---|---|
| Helper definition diverges between consumers if someone adds a new precompute loop later | The helper is a single function; misuse requires explicit re-implementation. AC-5 regression test would catch the most common new failure mode |
| Module + class basename collision (which IS legitimate — they share a name in `Foo.swift` containing `class Foo`) inflates same_name_node_count by 1 vs operator expectation of "the class" | Companion change `1316l-enh graph-builder-swift-class-module-merge` merges the pair, eliminating the inflation. Until that lands, operators see count=2 for class+module twins which is honest about the underlying graph shape |

## Related Work

- Direct response to Solaris field feedback on `1.2.1+315o` (Finding 1).
- Companion to `1316l-enh graph-builder-swift-class-module-merge` (Finding 2 — structural merge at index time).
- Fixes a latent bug introduced in wave 130rj (`130tw-enh fan-in-name-collision-hint-and-seed-note`) and surfaced by wave 13129's `file_hubs` section split (`1312d`) plus collision-count decomposition (`1312b`).

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
