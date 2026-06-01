# Decompose `name_collision_count` into `same_name_node_count` + `cross_file_collision` + `external_name_collision_count`

Change ID: `1312b-enh decompose-name-collision-count`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Two converging field reports on `1.2.0+312f` identified the `name_collision_count` field shipped in wave 130rj (130tw #5) as the wrong shape:

**Solaris (Swift, 2026-06-01):** `name_collision_count: 72` flagged a real anomaly on `StatusBarManager` (kind=module) but conflated two distinct signals:

1. **Same-file aggregation noise** — nested types, closure-scope helpers, and inner declarations defined inside one file all share the file's identifier prefix. For `StatusBarManager.swift` containing a top-level `StatusBarManager` class with 30 inner types, every same-name node lives in the same file's tree.
2. **Cross-file simple-name collisions** — multiple unrelated `process` symbols across distinct classes in distinct files. This is the actual signal an operator wants for fan_in trustworthiness.

Solaris's investigation needed 6 tool calls to verify the case was safe. With `(same_name_node_count: 72, cross_file_collision: false)` the safe verdict would have been visible inline.

**Aceiss (Java, 2026-06-01):** the *opposite* problem — `JSON.writeObject` reports `name_collision_count: 1` (correctly: one project node) but the *actual* conflation is with `java.io.ObjectOutputStream.writeObject` (an external symbol). External symbols aren't counted, so the field falsely declares "safe" when the project has a high-collision name shared with the JDK or framework classes. This is the **common case** for Java: `run` (Runnable), `close` (AutoCloseable), `equals`, `toString`, `accept`, `apply` — every project symbol with one of these names collides externally and the current field hides it.

The decomposed shape resolves both reports:

- **`same_name_node_count`** — project-only count (existing semantics; preserved)
- **`cross_file_collision`** — true when 2+ project files own a same-name node (Solaris signal)
- **`external_name_collision_count`** — count of `external::*` nodes sharing the simple name (Aceiss signal)

An operator reading any one entry sees: how many project nodes carry this name, whether they live in different files (cross-file risk), and whether the JDK or libraries also use it (external-collision risk). The three fields jointly answer "is this fan_in figure trustworthy?"

## Requirements

1. **Add `same_name_node_count: int` to each `fan_in` / `fan_out` / `chokepoints` / `betweenness` entry.** Same semantics as the current `name_collision_count` — counts distinct project-internal graph nodes that share the entry's symbol simple name.
2. **Add `cross_file_collision: bool` to each entry.** `True` when same-simple-name project nodes live in 2+ distinct source files; `False` when all same-simple-name nodes share one source file (same-file aggregation noise).
3. **Add `external_name_collision_count: int` to each entry.** Count of `external::*` nodes whose simple name matches the entry's symbol simple name. Value 0 means no JDK/framework class uses the name.
4. **Keep `name_collision_count` as a deprecated alias for `same_name_node_count`** for one release. Document deprecation in the field's docstring on `wave_graph_report`.
5. **Update seed-211 interpretation guidance:** the verification trigger becomes the OR of two signals — `(same_name_node_count > 1 AND cross_file_collision: true)` OR `(external_name_collision_count > 0)`. Same-file-only collisions with no external collision are trustworthy without verification.
6. **Precompute the per-symbol project-file-set AND external-count at report-build time** — single pass O(|nodes|) walking both project and `external::*` nodes.
7. **Tests** cover (a) cross-file project collision → fields set correctly; (b) same-file project aggregation → `same_name_node_count > 1, cross_file_collision: false`; (c) external-only collision (Aceiss case: `JSON.writeObject` with `external::ObjectOutputStream.writeObject` present) → `external_name_collision_count > 0`; (d) combined project + external collision; (e) unique-name entry → all defaults; (f) deprecated `name_collision_count` alias still present.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — replace simple-name → count map with simple-name → set-of-source-files map. Emit both new fields plus the deprecated alias.
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — update the interpretation guidance line.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — 4 regression tests + update the existing `TestNameCollisionCount` to assert the new fields.

**Out of scope:**

- Removing `name_collision_count` (kept as alias).
- Computing the file-set at index time (kept at request time — cheap, doesn't require index version bump).
- Same field on `code_graph_community` member entries (defer).

## Acceptance Criteria

- [ ] AC-1: Each `fan_in` / `fan_out` / `chokepoints` / `betweenness` entry carries `same_name_node_count: int` (same value as current `name_collision_count`).
- [ ] AC-2: Each entry carries `cross_file_collision: bool` — True when 2+ distinct source files own a same-simple-name project node, False otherwise.
- [ ] AC-3: Each entry carries `external_name_collision_count: int` — count of `external::*` nodes sharing the symbol's simple name.
- [ ] AC-4: `name_collision_count` field is still present and equal to `same_name_node_count` (deprecated alias).
- [ ] AC-5: Single O(|nodes|) precompute per request — measured negligible on 10k-node graphs.
- [ ] AC-6: Seed-211 interpretation line refers to both `cross_file_collision` and `external_name_collision_count` as combined verification triggers.
- [ ] AC-7: 6 regression tests cover the field semantics; all existing tests pass.
- [ ] AC-8: docs-lint passes after seed edit.

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] Replace simple-name → count map with simple-name → (project-file-set, external-count) map
- [ ] Emit `same_name_node_count` + `cross_file_collision` + `external_name_collision_count` on the 4 ranking sections
- [ ] Keep `name_collision_count` as deprecated alias
- [ ] Open `seed_edit_allowed` gate
- [ ] Update seed-211 interpretation line (combined trigger semantics)
- [ ] Run docs-lint
- [ ] Close `seed_edit_allowed` gate
- [ ] Add 6 regression tests; update `TestNameCollisionCount` for the new fields
- [ ] Run framework tests
- [ ] Close `framework_edit_allowed` gate
- [ ] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Backward-compat semantic preservation |
| AC-2 | required | Solaris signal — Swift same-file aggregation disambiguation |
| AC-3 | required | Aceiss signal — Java external collision (writeObject, run, close, etc.) |
| AC-4 | required | Deprecation alias keeps existing consumers working |
| AC-5 | required | Performance budget |
| AC-6 | required | Operator interpretation guidance |
| AC-7 | required | Regression coverage |
| AC-8 | required | docs-lint hygiene |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Keep `name_collision_count` as deprecated alias for one release | Existing consumers (Solaris, Aceiss) read the field. Removing would break round-trip. Alias preserves API stability while the new fields take over | Hard remove (rejected — breaks existing consumers); rename in place (rejected — silent semantic shift) |
| 2026-06-01 | `cross_file_collision: bool` rather than `distinct_file_count: int` | Boolean carries the operator-actionable signal directly. The exact distinct-file count is rarely meaningful — same-file (1) vs cross-file (≥2) is the decision boundary | Surface both bool + int (rejected — adds field for marginal precision) |
| 2026-06-01 | `external_name_collision_count: int` rather than `has_external_name_collision: bool` | The count is cheap to compute and tells the operator "1 JDK collision" vs "8 framework + JDK collisions" — the latter signals broader cross-library risk. Aceiss suggested the bool but the int subsumes it (test for `> 0` to get the bool semantics) | Boolean (rejected — drops gradational signal); both (rejected — duplicate surface) |
| 2026-06-01 | Compute at request time, not index time | Avoids `GRAPH_BUILDER_VERSION` bump and cache invalidation. Single O(|nodes|) pass adds <50ms on 10k-node graphs | Cache in index (deferred — bump cost not justified) |

## Risks

| Risk | Mitigation |
|---|---|
| Consumers reading only `name_collision_count` miss the new signal | Seed-211 update + deprecation note in docstring direct consumers to the new fields |
| O(|nodes|) precompute uses more memory than the previous count-only map | Set-of-strings per simple name; bounded by total source files (~thousands for realistic codebases); negligible |
| Solaris's `StatusBarManager` case was Swift; verify the file-set heuristic works for languages where one file can contribute to multiple simple-name node-id patterns | Test on a Java fixture (`com.foo.Inner.method` vs `com.bar.Inner.method` — same simple name "Inner" across files) |

## Related Work

- Direct response to converging field feedback on `1.2.0+312f`:
  - **Solaris (Swift)** — investigated `StatusBarManager (module)` with `fan_out: 77` flagged by `name_collision_count: 72`. The 72 was 100% same-file aggregation; misleading without `cross_file_collision`.
  - **Aceiss (Java)** — `JSON.writeObject` reported `name_collision_count: 1` despite real collision with `java.io.ObjectOutputStream.writeObject`. External symbols invisible without `external_name_collision_count`.
- Supersedes (but preserves) the `name_collision_count` field shipped in wave 130rj as `130tw-enh fan-in-name-collision-hint-and-seed-note`.
- Companion to the graph-builder receiver-type-attribution change in this wave — the fields are the *diagnostic* layer; receiver-type attribution at index time is the *fix* layer.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
