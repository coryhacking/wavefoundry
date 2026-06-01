# Fix `external_name_collision_count` — Stdlib Allowlist for the Java Common Case

Change ID: `1316p-enh external-name-collision-stdlib-allowlist`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Aceiss round-trip report on `1.2.1+315o` (2026-06-01): the `external_name_collision_count` field shipped in `1312b` was designed to catch the Java common case — symbols colliding with JDK/framework simple names (`run`, `close`, `equals`, `hashCode`, `toString`, etc.). After `1312l` shipped receiver-type resolution at the graph builder, the indexer no longer creates spurious `external::*` nodes for resolved calls. So the field now counts only **resolution residue** — `external::*` nodes the resolver couldn't disambiguate.

Concretely: `SpringUserListJob.run` and `JdbcUserListJob.run` both report `external_name_collision_count: 0` despite `java.lang.Runnable.run` and every Spring `Runnable` subclass colliding. `ReflectionUtil.getMethod` reports 0 despite `java.lang.Class.getMethod` colliding. The seed-211 verification trigger `external_name_collision_count > 0` effectively never fires for the cases it was designed to catch.

The field is honest about what it counts — but what it counts no longer answers the operator's question: *"could this fan-in number be inflated by JDK/framework name collisions the resolver might have missed?"*

## Approach

Replace the graph-state-based count with a curated allowlist of common Java stdlib + framework method simple names. When a project symbol's simple name appears in the allowlist, the field reports the membership.

The allowlist is small, focused on the dominant collision sources:

```python
_JAVA_STDLIB_COMMON_NAMES = frozenset({
    # java.lang.Object
    "equals", "hashCode", "toString", "getClass", "notify", "notifyAll", "wait",
    # java.lang.Runnable / Thread
    "run",
    # java.lang.AutoCloseable / Closeable
    "close",
    # java.util.function (Functional interfaces)
    "accept", "apply", "test", "get",
    # java.util.Comparator / Comparable
    "compare", "compareTo",
    # java.util.Iterator / Iterable
    "iterator", "next", "hasNext",
    # java.lang.reflect (commonly mistaken)
    "getMethod", "getDeclaredMethod", "getField", "getDeclaredField",
    # java.io
    "read", "write", "flush",
    # java.util.Map.Entry / collections
    "getKey", "getValue",
    # Spring patterns
    "execute", "process", "handle",
})
```

The field semantics shift from "count of external::* graph nodes" to "count of allowlist hits" (boolean-by-name with possible future per-name framework granularity).

To preserve the field's `int` shape: the count is `1` when the project symbol's simple name is in the allowlist (one collision source — the JDK/framework), `0` otherwise. Future expansion could differentiate JDK vs Spring vs Hibernate hits with values 1/2/3 etc. — defer until operator demand surfaces.

The deprecated alias `name_collision_count` continues to map to `same_name_node_count`; no change.

## Requirements

1. **New constant `_JAVA_STDLIB_COMMON_NAMES`** in `server_impl.py` with the curated allowlist (~25 names).
2. **`_collision_fields` consults the allowlist** for `external_name_collision_count` instead of `external_counts_by_simple_name` from the graph. The graph-state-based map can be removed from the precompute.
3. **The seed-211 verification trigger documentation** is updated to clarify: `external_name_collision_count: 1` now means "the simple name is a known Java stdlib/framework method name; verify with code_callhierarchy on the specific node_id".
4. **Tests** cover (a) `run` triggers `external_name_collision_count: 1`; (b) `myCustomMethod` triggers 0; (c) symbol entries on non-Java languages get 0 (the allowlist is Java-focused; future waves can add per-language allowlists when operator-validated).
5. **Existing test `test_external_only_collision_surfaces_count`** in `TestExternalNameCollisionCount` updates to reflect the new semantics (the test currently asserts count 2 for two `external::*` nodes; under the new semantics it asserts count 1 for any allowlist hit OR 0 for non-allowlist names — pick the case that documents the intent).

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — `_JAVA_STDLIB_COMMON_NAMES` constant + `_collision_fields` rewrite.
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — verification trigger note clarifies allowlist semantics.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — 3 new tests + adjust `test_external_only_collision_surfaces_count`.

**Out of scope:**

- Per-language allowlists for C# / Kotlin / Swift / Python. Java is the dominant operator-reported case; add others on operator validation.
- Subdividing the count into JDK vs Spring vs framework-specific hits. Defer.
- Removing the field entirely (Aceiss's option C). The decomposition has value; the fix is to make it count the right thing.
- Per-name framework attribution (e.g., `run` could attribute to Runnable; `getMethod` to Class). Defer.

## Acceptance Criteria

- [x] AC-1: `_JAVA_STDLIB_COMMON_NAMES` constant exists with the curated allowlist (~25 names covering Object / Runnable / AutoCloseable / Functional interfaces / Comparator / Iterator / reflect / IO / Map.Entry / common Spring patterns).
- [x] AC-2: `_collision_fields` reports `external_name_collision_count: 1` when the simple name is in the allowlist, `0` otherwise. The previous graph-state precompute (`external_counts_by_simple_name`) is removed.
- [x] AC-3: Seed-211 verification trigger note updated to document the allowlist semantics. **Plus the `wave_graph_report` MCP wrapper docstring for `external_name_collision_count`** is updated inline to describe the allowlist semantics — operators inspecting the schema via FastMCP introspection must see the current behavior, not the wave-1312b graph-state description. (Council action item: code-reviewer + red-team.)
- [x] AC-4: Java symbols with simple names like `run`, `close`, `equals` trigger count: 1. Non-allowlist names trigger 0.
- [x] AC-5: Java-focused; non-Java symbols don't trigger the allowlist (the field's interpretation is Java-specific in this release).
- [x] AC-6: 3 new regression tests + 1 updated test cover the behavior; all existing tests pass.
- [x] AC-7: docs-lint passes.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `_JAVA_STDLIB_COMMON_NAMES` constant
- [x] Rewrite `_collision_fields` to consult the allowlist
- [x] Remove the graph-state-based external precompute (no longer needed)
- [x] Open `seed_edit_allowed` gate
- [x] Update seed-211 verification trigger note
- [x] Run docs-lint
- [x] Close `seed_edit_allowed` gate
- [x] Add 3 regression tests; update the existing external-collision test
- [x] Run framework tests
- [x] Close `framework_edit_allowed` gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The allowlist is the field's new source of truth |
| AC-2 | required | The semantic shift |
| AC-3 | required | Operator interpretation guidance |
| AC-4 | required | The Aceiss-reported common cases now trigger correctly |
| AC-5 | required | Scope discipline — Java-focused; other languages added on demand |
| AC-6 | required | Regression coverage + update existing assertion |
| AC-7 | required | docs-lint hygiene |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Allowlist over rejected-receiver-resolution residue tracking | Aceiss's option (1) — track rejected resolution candidates — is complex and changes the indexer to maintain a separate index. The allowlist is simple, focused, and answers the operator's actual question ("is this name commonly collided?") | Track rejected resolutions at indexer (rejected — complex; the allowlist's curated set covers the dominant cases without bookkeeping); rename + add `stdlib_simple_name_match: bool` (rejected — adds API surface; the count subsumes the bool semantics via `> 0`) |
| 2026-06-01 | Java-only allowlist initially | Aceiss reported Java specifically. C# / Kotlin / Swift / Python each have different stdlib patterns; pre-emptive multi-language allowlists are over-scoped without operator validation | Multi-language allowlist (rejected — no operator validation for non-Java) |
| 2026-06-01 | Count returns 0 or 1, not graduated framework attribution | The decomposed field's primary signal is "is this fan-in suspicious for stdlib collision?" — boolean-as-int. Graduated values (JDK=1, Spring=2, etc.) add interpretation complexity for marginal benefit | Per-framework counts (deferred — operator-validation-driven) |
| 2026-06-01 | Keep the field's name | Renaming to `unresolved_external_name_count` (Aceiss's option 2) describes the OLD behavior. The new behavior is closer to the original field name's spirit. Rename would also break the deprecated `name_collision_count` alias's documented relationship with the decomposed fields | Rename to `stdlib_simple_name_match` (rejected — boolean shape loses count granularity); rename to `unresolved_external_name_count` (rejected — describes old behavior, not the new design) |

## Risks

| Risk | Mitigation |
|---|---|
| Allowlist misses a common name an operator reports as "should have flagged" | Operator reports are the right validation cycle; the allowlist is easy to extend |
| Allowlist over-flags a name that's legitimately the project's unique method (e.g. project defines its own `close` that no JDK class collides with semantically) | The flag is a "verify with code_callhierarchy" trigger, not a verdict. False positives lead to one extra verification call — acceptable cost |
| Future operator wants the rejected-resolution-residue signal back | Document the design trade-off in the change-doc decision log; restore via a sibling field if operator demand surfaces |

## Related Work

- Direct response to Aceiss field feedback on `1.2.1+315o` (Finding 2).
- Replaces the graph-state precompute for `external_counts_by_simple_name` introduced in `1312b`.
- Companion change in the same wave: `1316j-enh fix-module-simple-name-extraction` (Finding 1 — the module simple-name bug); `1316n-enh graph-rebuild-discoverability-and-health`; `1316r-enh stable-community-identifier`; `1316t-enh empty-section-diagnostic-fields`; `1316l-enh graph-builder-swift-class-module-merge`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
