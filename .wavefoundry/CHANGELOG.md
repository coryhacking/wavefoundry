# Wavefoundry Changelog

Operator-facing release history for the wavefoundry framework. Sections are organized by semver version (`MAJOR.MINOR.PATCH`) with git-commit-style summary bullets describing what each release delivers. The latest release appears first.

This file is at the project-level path (`.wavefoundry/CHANGELOG.md`) rather than inside `.wavefoundry/framework/`. Downstream consumer projects receive the file as a snapshot of release history at upgrade time; they do not edit it locally.

---

## 1.3.31 — 2026-06-03

Two perf wins layered on the 1.3.30 parallel-extraction architecture. No `GRAPH_BUILDER_VERSION` bump.

**1. Parallel source-file reads in the parent.** `update_graph_index` previously read all `files` serially before bucketing into code / doc work lists — on Teton-scale builds (1,500+ files) that's a measurable single-threaded I/O stage in front of the parallel extraction. Now uses a `ThreadPoolExecutor` (8 workers cap, `min(cpu_count, 8, len(files))`) over the read loop. `Path.read_text` releases the GIL during the syscall so multiple reads issue concurrently against the page cache. Gated by the same `_PARALLEL_EXTRACTION_THRESHOLD=100` file-count gate — small / incremental builds stay serial.

**2. In-place cross-file rewrite.** The cross-file resolution pass that rebinds `external::*` edges to project nodes previously built a fresh `new_edge_map` and reassigned `edge_map = new_edge_map` on every build. On Teton-scale (~77,000 edges, ~2,000 rewrites) the allocation of a full duplicate dict was a measurable share of finalize wall time. The rewrite now collects `(old_key, new_key, new_edge)` tuples in a small list (only for edges that actually rewrite) and applies them in place after the iteration completes. Output is byte-identical to the previous behavior — the `setdefault` collapse on duplicate keys is preserved.

Both wins are modest individually (sub-second on synthetic 1,542-file workloads) but compound — the goal is to chip away at the ~5s post-extraction window Teton sees between the worker pool draining and the "cross-file resolution rewrote N edges" log line. Honest expectation: 5-15% wall-time improvement on Teton-scale, not a 44%-style transformative win.

Agent-facing CLI helper docs from 1.3.30 (`upgrade-wavefoundry --detect-zip` / `--list-zips`) now propagated to **both** seed-160 (canonical) and `docs/prompts/upgrade-wavefoundry.prompt.md` (rendered). The rendered prompt now contains the `ls -1` antipattern warning so agents reading the prompt directly see why they shouldn't visually inspect the dist directory.

Verified: 2260 framework tests pass.

---

## 1.3.30 — 2026-06-03

Two operator-facing surfaces:

**1. Parallel code-file graph extraction.** Spawn-mode `ProcessPoolExecutor` extracts code-file artifacts across worker processes, auto-scaled to the machine's performance-core count (P-cores on Apple Silicon detected via `sysctl hw.perflevel0.physicalcpu`; `cpu_count() // 2` fallback on Linux/Windows SMT). Output is byte-identical to serial extraction. Field measurement on a 1,542-TS-file Nx monorepo: **27.1s serial → 15.07s parallel-8 (44% faster)**.

Design choices:

- **Threshold-gated** at 100 code files (`WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD` env var override). Small builds, incremental hook-triggered reindexes, and test fixtures stay on the serial path so they don't pay per-worker spawn cost.
- **Auto-scale tiers** by file count: `<200 → 2 workers`, `200-499 → 3 workers`, `≥500 → P-core count` (capped at the system's actual P-cores). `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS=N` overrides the auto-scaled count unconditionally.
- **Process backend by default** — `WAVEFOUNDRY_GRAPH_PARALLEL_BACKEND=processes`. Each worker has its own GIL; per-task work parallelizes cleanly across cores after the per-task state load was hoisted out of the worker path. A thread backend (`=threads`) is preserved as opt-in for workflows with many small partial rebuilds where the per-process spawn cost would dominate the small case.
- **State + gitattrs pre-loaded in the parent and shared with workers via worker_args.** Eliminates per-task `_load_state()` JSON parse and `.gitattributes` disk scan that previously serialized on the GIL across worker threads — the difference between thread-mode losing to serial and processes beating serial by 44%.
- **Worker-side `git ls-files` subprocess skipped** when the per-task `GraphIndexSession.__init__` receives an empty `files=[]` list. Cuts ~1,500 redundant `git` fork+exec invocations per large build and closes a macOS spawn-mode hazard where `subprocess.Popen.__init__`'s internal `select.poll().poll()` for fork-completion could deadlock from inside an already-spawned worker.
- **Graceful fallback to serial** on any pool failure. The build always completes.
- **Doc/seed extraction stays serial** because it depends on cross-file `symbol_terms` built across all artifacts.
- **Diagnostic breadcrumbs** at every transition in the parallel branch (only when `--verbose`), with thread-count tags. Pinpoints which step blocks if a future regression deadlocks the pool.

Env-var override surface:

- `WAVEFOUNDRY_GRAPH_PARALLEL_BACKEND` — `processes` (default) or `threads`.
- `WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD` — minimum code-file count to enter the parallel path (default `100`).
- `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` — hard worker-count override (default: auto-scale).
- `WAVEFOUNDRY_GRAPH_PARALLEL_START_METHOD` — `spawn` (default) / `fork` / `forkserver` escape hatch.

**2. Agent-facing upgrade CLI helpers.** Two new flags on `.wavefoundry/bin/upgrade-wavefoundry`:

- `--detect-zip` — prints the absolute path of the highest-semver `wavefoundry-*.zip` across all four search paths (repository root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`), then exits `0`. Exits `1` with empty output if no matching zip is found. Agents that previously fell back to `ls -1` to determine the latest pack should use this instead — `ls -1` sorts lexicographically and ranks `1.3.9` *above* `1.3.30`, which made agents apply stale packs.
- `--list-zips` — prints every matching pack across all four search paths, semver-sorted (highest first), with the selected-latest prefixed by `* `. Use when you need the full inventory.

Seed-160 (`160-upgrade-wavefoundry.prompt.md`) updated to direct agents to these flags instead of `ls -1`. When MCP is attached, `wave_upgrade(mode='dry_run')` continues to surface the selected pack on a `Zip to apply:` line and remains the preferred path.

Other internal optimizations rolled up into this release:

- Single-pass TS/JS extractor walker: previous walker traversed each AST twice (once for definitions, once for calls). Merged into a single pass with buffered call resolution post-walk. Reduces per-file walker wall-time materially on large source files.
- `lru_cache(maxsize=20000)` on path-resolution helpers (`_probe_ts_alias_target`, `_resolve_relative_ts_import`) for barrel-export-heavy codebases where each unique specifier is hit dozens of times per build.
- `_TS_FILE_DECLARED_NAMES_CACHE` keyed on (path, mtime) so the barrel walker hits cache instead of re-running its declared-names regex pass per file.

Verified: 2260 framework tests pass.

---

## 1.3.17 — 2026-06-02

Operational-polish patch on 1.3.16. No `GRAPH_BUILDER_VERSION` bump, no auto-rebuild on upgrade, no extractor-shape changes — output is identical to 1.3.16.

Three index-build / auto-rebuild defects fixed together because they form one user-visible failure mode (Teton field session, post v22→v23 upgrade):

- **`wave_index_build` no longer returns misleading success when the spawned subprocess fails to acquire the lock.** `run_index_rebuild` now polls `proc.poll()` for a brief verification window (1.5s default, configurable via `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS`) after Popen. If the subprocess exits inside the window with a non-zero code, the response returns `passed: false`, `build_failed_early: true`, sets `graph_rebuilt: false`, and surfaces a `build_skipped_lock_busy` diagnostic carrying the lock-holder PID. `wave_index_build_response` also skips cache invalidation and the post-rebuild MCP resource dispatch on the early-exit path so downstream consumers see consistent state.
- **`_index_build_lock` proactively unlinks stale lock-file metadata before attempting `flock()`.** When `classify_index_build_lock_owner` returns `"stale"` (recorded PID is dead) and the lock file exists, `lock_path.unlink()` runs ahead of the `open()`. Downstream tools that read the metadata file (status surfaces, diagnostic messages) now see fresh post-acquire content instead of the legacy dead-PID metadata. Unlink races are handled (POSIX `unlink` doesn't affect file descriptors already open in other processes; `FileNotFoundError` is caught).
- **`_ensure_graph_builder_current` coordinates concurrent auto-rebuild attempts within a single MCP server process.** A module-level `_VERSION_REBUILD_INFLIGHT` dict keyed on `(root, layer)` and guarded by `_VERSION_REBUILD_INFLIGHT_LOCK` records the start time of any in-flight rebuild. Concurrent callers that detect the same builder-version mismatch and see the marker return a `graph_auto_rebuild_in_progress` diagnostic (with `rebuild_started_at_age_seconds`) instead of racing for the index-build flock and emitting the noisy `graph_auto_rebuild_failed` spam Teton observed. The marker is released on every exit path (success, failure, unhandled exception) via `try/finally`. A 120s stale-inflight safety net (`_INFLIGHT_REBUILD_STALE_SECONDS`) prevents a crashed rebuild from pinning the marker indefinitely.

Verified: 2251 framework tests pass (was 2246 — net +5 regression tests):

- `test_stale_lock_file_is_unlinked_before_acquire` (Bug 1 / AC-3)
- `test_subprocess_early_exit_with_lock_busy_surfaces_failure` (Bug 2 / AC-1)
- `test_concurrent_auto_rebuild_defers_via_inflight_marker` (Bug 3 / AC-4)
- `test_stale_inflight_marker_allows_fresh_rebuild_attempt` (Bug 3 / AC-5)
- `test_inflight_marker_released_on_success_and_failure` (Bug 3 / safety net for the in-flight marker)

---

## 1.3.16 — 2026-06-02

**Operator action required.** `GRAPH_BUILDER_VERSION` bumps 22 → 23 — every consumer project rebuilds its graph index on next `wave_index_build` / next MCP-server warmup after upgrade. Rebuild duration scales with code volume (small projects ≈ seconds; Teton-scale 12k-node Nx monorepos ≈ 60–90s). **Affects TypeScript and JavaScript only** — other languages produce byte-identical output to 1.3.15.

What changes in the graph: TS/JS call edges that previously landed as `EXTRACTED` despite the indexer having bound the target deterministically now land as `RECEIVER_RESOLVED`. Two specific paths get the upgrade:

- **Intra-file (and locally-defined) bare-identifier calls.** When `_ts_resolve_target` returns a project-internal node directly — covering intra-file arrow-const callers like `getRootToken()` referenced from a sibling function in the same file — the binding came from `symbol_lookup` (exact name match in the file's own definition table). Pre-1.3.16 tagged these `EXTRACTED`. They are high-confidence by construction.
- **Cross-file bare-identifier calls with unambiguous project-wide match.** The cross-file rewrite pass's AC-1 branch (bare simple name in `simple_name_index` with exactly one candidate) now promotes the rewritten edge from `EXTRACTED` to `RECEIVER_RESOLVED` when the source file is TS/JS. AC-2 (qualified-target simple-name fallback for shapes like `obj.method()` where `obj` is unannotated) intentionally remains `EXTRACTED` because that branch is a type guess, not a deterministic bind.

Field signal that drove the fix: Teton's `getRootToken` had 5 incoming intra-file callers all landing as `EXTRACTED` on v22, invisible to `attribution_counts_by_language["typescript"]["receiver_resolved"]`. The total TS resolved-share sat at 8.3% (3,083 receiver_resolved + 810 construction_resolved / 47,034 attributed). The intra-file bucket alone is likely the largest single source of misclassified-confidence edges on arrow-const-heavy codebases.

Out of scope this round: cross-file qualified-target rewrites (the AC-2 simple-name fallback) and non-TS/JS languages. Field data after this rebuild will indicate whether a follow-up promotion is warranted for those paths.

Verified: 2246 framework tests pass, including 2 new regression tests — `test_intra_file_arrow_const_call_lands_receiver_resolved` covers the intra-file path, `test_cross_file_unique_simple_name_call_lands_receiver_resolved` covers the AC-1 cross-file path.

---

## 1.3.13 — 2026-06-02

Pure performance patch on 1.3.12 — no extractor-shape changes, no `GRAPH_BUILDER_VERSION` bump, no auto-rebuild needed on upgrade.

Path-resolution helpers (`_probe_ts_alias_target`, `_resolve_relative_ts_import`) are pure functions of `(args, filesystem state)`. On barrel-export-heavy codebases, each unique import specifier is hit dozens of times during a build (once per caller) — without caching, every hit re-runs the path probe and its associated `is_file()` syscalls. `functools.lru_cache(maxsize=20000)` turns repeated calls into O(1) lookups within a build. Caches survive across builds within a single MCP server process; LRU eviction handles size naturally, and stale-result risk is low because deleted files don't appear in the per-build file list.

Builds on barrel-heavy TS/JS monorepos (Teton-shape) should see additional wall-time reduction beyond the 1.3.12 file-declared-names cache. Test suite wall-time unchanged because each test uses a unique tmp directory so caches rarely hit on tiny build calls — the gains are workload-dependent.

---

## 1.3.12 — 2026-06-02

> **Operator-action note: graph builder version bumped 21 → 22.** First MCP query against the graph layer after upgrade will trigger a one-time synchronous rebuild (~10–30s on typical projects; ~50–60s on 12k-node monorepos with this release's perf fix; previously ~80s).
>
> Affects **TypeScript and JavaScript only**, and the impact on attribution counts is substantial. Repos that use **relative imports for intra-package calls** to **arrow-const-bound functions** (the modern Lambda + Nx + Node.js pattern) should see `attribution_counts_by_language["typescript"]["receiver_resolved"]` rise materially after the rebuild. The 1.3.11 release added the function nodes for arrow-const declarations but couldn't attribute calls to them as RECEIVER_RESOLVED when the caller used a relative import (`import { x } from './events'`) because the relative-path prefix was lost in the resolver pipeline. This release closes that gap.
>
> Also: rebuild time on barrel-export-heavy codebases drops materially (Teton-shape projects: 79s → ~50s estimated) because barrel walking now caches per-file declaration sets instead of re-reading destination files on every name lookup.

Same-day continuation of the v21 arrow-const work. Teton field validation on 1.3.11 confirmed all three smoke targets resolve and total TS edges grew 26% — but +9,379 of the new edges landed as `EXTRACTED` rather than `RECEIVER_RESOLVED` because intra-package callers using relative imports went through a code path that lost the relative-path prefix at `_ts_clean_name` time. The fix: extract the raw module specifier before cleaning, then branch on relative vs alias resolution. Plus the perf fix the barrel walker needed.

### Changes

- Bump `GRAPH_BUILDER_VERSION` 21 → 22. See the operator-action note above
- Extract the raw module specifier from import statements with `./` / `../` / `/` / `@scope/` prefixes preserved. The existing `_ts_relation_candidates → _ts_clean_name` path stripped relative prefixes (`./events` → `events`), so the resolver couldn't tell relative imports apart from bare names. New `_ts_extract_import_module_specifier` helper reads the raw text from the import statement's `source` field
- Resolve relative imports against the source file's directory before the tsconfig.paths fallback. `import { x } from './events'` now resolves to the actual project file via `_resolve_relative_ts_import`, runs through the same barrel walker, and populates `import_targets` with the walked-through definition file. Direct calls to those imports promote to `RECEIVER_RESOLVED`
- Cache per-file top-level declaration sets keyed on `(path, mtime)`. `_file_declares_name` now reads through `_file_declared_names` which parses each destination file at most once per build. Eliminates the redundant file-read + regex-run loop in `_resolve_through_barrel` — for barrel-export-heavy codebases this is the dominant hot path

---

## 1.3.11 — 2026-06-02

> **Operator-action note: graph builder version bumped 20 → 21.** First MCP query against the graph layer after upgrade will trigger a one-time synchronous rebuild (~10–30s on typical projects; ~70–90s on 12k-node monorepos). The 131e2 safety net handles this automatically.
>
> Affects **TypeScript and JavaScript only**, and the impact is large on modern codebases. Repos that define functions as `export const foo = async (args) => { ... }` (arrow-const, the dominant shape in TS Lambda / Nx / React layouts) should see `attribution_counts_by_language["typescript"]["receiver_resolved"]` rise materially — Teton's field validation estimates 6% → 30–60% on the canonical Nx + Lambda shape because arrow-const previously didn't register as a graph node at all. Repos using `function foo()` declarations exclusively should see no change. Repos in other stacks rebuild but their attribution numbers shouldn't shift.

Same-day post-ship correction on 1.3.10. Teton confirmed v19 → v20 worked end-to-end — TS receiver-resolved share jumped 4.3% → 6.0% with +641 RECEIVER_RESOLVED edges as an exact migration. But three smoke-test symbols still returned `graph_symbol_not_found` with a sharp diagnostic: every backend function in their codebase is `export const X = async (...) => { ... }` (zero hits on `^function ` or `^export function `). The arrow-const shape parses as `lexical_declaration → variable_declarator → arrow_function` in tree-sitter, and our extractor never descended through `variable_declarator` to find the identifier — so the symbol never registered as a graph node.

### Changes

- Bump `GRAPH_BUILDER_VERSION` 20 → 21. See the operator-action note above
- Register arrow-function-bound and function-expression-bound `const` declarations as function symbols. Detects `lexical_declaration` / `variable_statement` nodes whose child `variable_declarator` binds an `arrow_function` or `function_expression`, registers each as kind `function` (not `variable`), and walks scope through the arrow body so calls FROM inside arrow-const-bound functions attribute to the const name rather than the file. Covers both registration (`walk_definitions`) and edge-source attribution (`walk_calls`). This is the load-bearing change for the dominant function shape in modern TS — particularly Lambda + Nx layouts where free-function arrow-const is virtually the only pattern. End-to-end verified on the barrel + aliased-import + arrow-const stack: `caller → libs/utils/src/lib/http-request.ts::httpRequester` lands `RECEIVER_RESOLVED` regardless of whether either side uses `function` or arrow-const

---

## 1.3.10 — 2026-06-02

> **Operator-action note: graph builder version bumped 19 → 20.** First MCP query against the graph layer after upgrade will trigger a one-time synchronous rebuild (~10–30s on typical projects; ~70s on 12k-node monorepos). The 131e2 safety net handles this automatically.
>
> Affects **TypeScript and JavaScript only.** Repos on barrel-export-heavy library layouts where most imports are **free functions** (not methods on classes) should see `attribution_counts_by_language["typescript"]["receiver_resolved"]` rise materially after the rebuild — Teton-shape codebases were the motivating case. Repos in other stacks rebuild but their attribution numbers shouldn't shift.

Same-day post-ship correction on 1.3.9, motivated by Teton field validation that confirmed three things at once: the v18 → v19 bump fired correctly and community structure shifted (proving the leading-`@` fix + tsconfig.paths now work end-to-end), but attribution numbers stayed byte-identical at 4.3% and community labels regressed to generic `"src/index N"`. Root cause for the unchanged attribution: 1.3.9's barrel walker only fired on method calls (`obj.method()`), not direct function calls (`func()`) — and most aliased imports on real Nx codebases are free functions, not class methods.

### Changes

- Bump `GRAPH_BUILDER_VERSION` 19 → 20. See the operator-action note above
- Promote direct-function-call edges through `import_targets` to `RECEIVER_RESOLVED`. When the call resolves to `external::<name>` AND `import_targets` carries a walked-through definition file for that bare name, the edge target is rewritten to `<definition_file>::<name>` and confidence rises from `EXTRACTED` to `RECEIVER_RESOLVED`. This is the load-bearing fix for the persistent 4.3% TS-resolved rate on barrel-export-heavy monorepos: most aliased imports on those layouts are free functions
- Bundler-mode `.js` / `.jsx` / `.mjs` / `.cjs` → `.ts` / `.tsx` / `.mts` / `.cts` extension swap in `_probe_ts_alias_target`. TS 5.x's `moduleResolution: "Bundler"` (Vite / esbuild / Nx defaults) allows source code to write `./foo.js` and resolve to `./foo.ts` at compile time. Barrel re-exports written this way now walk through correctly
- Community-label seed selector deprioritizes barrel files (`index.{ts,tsx,js,jsx,mjs,cjs,mts,cts}`). Barrels accumulate high in-degree once aliased imports resolve to them; without deprioritization Leiden picks barrels as seeds and meaningful labels collapse to generic `"src/index N"`. Barrels still get the seed when they're the only candidate in a community. `hub_node_id` unchanged so operators caching by stable-reference contract are unaffected

---

## 1.3.9 — 2026-06-02

> **Operator-action note: graph builder version bumped 18 → 19.** First MCP query against the graph layer after upgrade will trigger a one-time synchronous rebuild (~10–30s on typical projects). The 131e2 safety net handles this automatically — no operator step required — but the rebuild pause is real.
>
> Affects **TypeScript and JavaScript only.** Repos in other stacks (Java, Python, Swift, etc.) will rebuild but their attribution numbers should not shift. Consumer projects on barrel-export-heavy library layouts (the dominant Nx pattern: every package's `src/index.ts` re-exports from `./lib/<name>`) should see their `attribution_counts_by_language["typescript"]["receiver_resolved"]` count rise materially after the rebuild — that's the load-bearing change.

Round-7 field-feedback patch on 1.3.8, motivated by Teton's configuration supplement on the persistent 4.3% TS receiver-resolved rate. The supplement identified barrel re-export following as the missing primitive; implementing it surfaced a second latent bug in `_ts_clean_name` that was the actual root cause of every scoped-import resolution failing across 1.3.6 / 1.3.7 / 1.3.8.

### Changes

- Bump `GRAPH_BUILDER_VERSION` 18 → 19. See the operator-action note above
- Follow barrel re-exports during TS/JS import resolution. tsconfig.paths aliases on Nx-shaped monorepos point at `src/index.ts` files that re-export from `./lib/<name>`. The receiver-type resolver now walks the re-export chain (`export { Foo } from './path'`, `export { Foo as Bar } from './path'`, `export { default as Foo } from './path'`, `export * from './path'`) until it reaches the actual definition file. `import_targets[name]` points at the definition file rather than the barrel index, so cross-package call edges land with per-symbol granularity instead of collapsing onto N hub nodes
- Preserve a leading `@` in `_ts_clean_name`. The helper was stripping the `@` prefix from scoped specifiers (`@aceiss/hooks` → `aceiss/hooks`) before any downstream consumer saw them, so tsconfig.paths patterns whose keys start with `@` never matched. Every npm scoped package (`@aws-sdk/*`, `@nestjs/*`, `@nx/*`, `@scope/*`) was silently mangled. This is the load-bearing root cause of Teton's 4.3% rate persisting across 1.3.6 / 1.3.7 / 1.3.8 — our 1p2tf code was structurally correct but never saw a specifier the alias map could match. Fix surfaced during 1p2tz barrel-resolver implementation; both fixes ship together
- Per-file barrel-parse cache keyed on `(path, mtime)` so each barrel file is parsed at most once per build. Recursion bound at 5 hops with cycle-set detection on resolved paths
- Alias collision handled correctly: when two aliases point at the same physical file (Teton's `@aceiss/hooks` and `@teton/hooks` both → `libs/hooks/src/index.ts`), both resolve through the same barrel chain to the same definition file with no duplicate edges

---

## 1.3.8 — 2026-06-02

> **Operator-action note: graph builder version bumped 17 → 18.** First MCP query against the graph layer after upgrade will trigger a one-time synchronous rebuild (~10–30s on typical project sizes). The 131e2 safety net handles this automatically — no operator step required — but the rebuild pause is real. Operators wanting to amortize it explicitly can run `wave_index_build(content='graph')` before their first query session.
>
> The bump invalidates consumer caches for extractor-shape changes shipped in 1.3.5 / 1.3.7 that previously couldn't take effect against pre-1.3.8 graphs: `.gen.ts` / `.generated.ts` JS-TS generated-file classifier (1p2q9 C), cross-file receiver-type resolution via tsconfig.paths-resolved imports (1p2tf), and `self_edge_kind` edge tagging on overloadable-language self-edges (1p2td). Affects all extracted languages — Java / Kotlin / C# / Swift / Scala / C++ for the overload tagging, TypeScript / JavaScript for the receiver-type and classifier changes.

Same-day patch on 1.3.7 covering three corrections surfaced by post-ship field validation: the builder-version bump above (the load-bearing change), a `self_edge_kind` propagation gap in `code_callhierarchy` entries, and a reconsidered seed-emit that turned out to be duplicate-of-code-defaults noise.

### Changes

- Bump `GRAPH_BUILDER_VERSION` from `17` to `18`. See the operator-action note above for the operational impact; without this bump, the extractor-shape changes shipped in 1.3.5 and 1.3.7 cannot take effect on existing consumer projects because the auto-rebuild only fires when state version mismatches runtime
- Propagate edge `self_edge_kind` to the `outgoing` and `incoming` entries returned by `code_callhierarchy`. The entry constructor reads the target/source node and was discarding the edge's overload-classification metadata before the response was assembled — consumers reading the list saw plain entries with no field. Now the field passes through; recursion / overload_forwarding / unknown surfaces alongside the call entry
- Drop the `code_navigation_hints` block emission from the install seed and the upgrade-time backfill rule. The block was pure duplication of code defaults — the resolver already falls back to `["return", "throw", "raise", "guard", "assert"]` when the key is absent — so emitting it added noise without functional effect. Operators tuning guard tokens still find the schema in seed-211; the workflow-config skeleton stays clean

---

## 1.3.7 — 2026-06-02

Round-5 field-feedback patch covering Teton's TypeScript receiver-resolution gap, javaagent's overload self-edge ambiguity, the workflow-config navigation-hints discoverability gap, and a long-standing self-hosting prune-safety bug that was silently deleting framework test files on every release.

### Changes

- Bridge tsconfig.paths-resolved imports into TypeScript / JavaScript receiver-type resolution. The 1.3.6 import-aliasing fix made `imports` edges bind to project files but the receiver-type resolver never consulted that map, so calls on imported types still fell through to `external::*`. Per-file `import_targets` is now populated at import-edge emission and consulted by `_resolve_ts_call_target` after the local symbol-lookup miss — aliased cross-package types resolve to project nodes with `RECEIVER_RESOLVED` confidence. Closes Teton's 4.3% type-resolved rate on strict-TS Nx monorepos
- Detect Nx project structure (`nx.json` at repo root) and surface as a diagnostic field on graph payloads. Wiring scaffolds future Nx-aware resolver passes; the detection alone enables operator-side reasoning about per-codebase resolution quality
- Tag `calls` self-edges on overloadable languages (Swift / Java / Kotlin / C# / Scala / C++) with `self_edge_kind`: `recursion`, `overload_forwarding`, or `unknown`. The per-file qname merge that collapses overloads into one node previously made every overload-forwarding call indistinguishable from recursion. Per-language signature extractors (Swift label fingerprints; arity for the positional languages) plus walker scope tracking plus an explicit classifier let consumers tell the two apart. Merged nodes carry `param_signatures` listing every overload's signature
- Emit a `code_navigation_hints` block with the language-default `guard_tokens` array in the workflow-config skeleton at install time, plus a backfill rule in the upgrade seed (never overwrites operator tuning). Operators tuning guard tokens see the schema in context instead of constructing the block from scratch after reading seed-211
- Remove the legacy fallback from `prune_framework.py`. The list was unconditionally deleting `scripts/tests/` and `scripts/run_tests.py` on every self-hosted upgrade because `build_pack.py` deletes `MANIFEST` after writing it into the zip, leaving `upgrade-wavefoundry` without an old manifest to diff against. No-old-manifest now logs a skip notice and returns — diff-based prune remains the only deletion path

---

## 1.3.6 — 2026-06-02

Continuation of wave 1p2q3 — completes the Nx TypeScript graph-extraction work, adds the per-language attribution diagnostic, redesigns the dashboard node-kind palette, and applies the dashboard flicker fix. Pairs with 1.3.5; field validation can run against either build.

### Changes

- Honor `tsconfig.json` / `tsconfig.base.json` `paths` aliases in TypeScript/JavaScript import resolution so Nx-style `@scope/lib` imports bind to the real project node id instead of dropping to `external::*`. Walks file directory upward to find the nearest tsconfig with `paths`; caches per-tsconfig; JSONC-aware parser preserves `//` inside string literals so URL strings and path patterns survive
- Add `attribution_counts_by_language` field to `code_callhierarchy`, `code_impact`, `code_definition`, and `wave_graph_report` responses. Shape: `{language: {receiver_resolved, construction_resolved, extracted}}` computed from the edges surfaced in the response. Operators can spot per-language coverage gaps at a glance (e.g. `{typescript: {receiver_resolved: 0, extracted: 3892}}` flags a resolver that isn't engaging)
- Rewrite the empty-graph-result fallback rule in `seed-211`, `code-reviewer.md`, `security-reviewer.md`, `architecture-reviewer.md` from a static less-mature-language list to a response-shape condition: if `code_callhierarchy` / `code_impact` returns empty AND `code_references` returns hits, treat the empty graph result as a coverage gap regardless of language
- Redesign dashboard node-kind palette for pairwise-distinct hues across all 10 kinds: add `variable` (vivid red), collapse `seed` into the `doc` bucket (seeds are markdown prompts — semantically documents), shift `external` from neutral grey to light blue-grey so it no longer reads as a pair with `doc` charcoal, shift `community` to emerald and `package` to bright cyan so they part visually, shift `namespace` to magenta so it parts from `class`
- Eliminate the dashboard graph-refresh flicker: gate the "Loading graph…" banner on initial load only, short-circuit `setGraph` when the incoming snapshot signature matches the prior, preserve operator selection across refreshes when the selected node still exists

---

## 1.3.5 — 2026-06-02

Round-4 field-feedback patch covering Aceiss's spurious-path report on `code_graph_path`, Teton's TypeScript/Nx-monorepo coverage gaps, an MCP cache-invalidation gap on graph rebuilds, and consumer-project pollution from framework-scripts indexing.

### Changes

- Rewrite `code_graph_path` shortest-path search as a weighted Dijkstra: `calls`/`RECEIVER_RESOLVED`=1, `calls`/`EXTRACTED`=2, structural=100. Treat `external::*` nodes as non-transitive intermediates — they remain valid endpoints but cannot bridge two real symbols, eliminating the spurious 2-hop paths that masked direct call chains. Add `min_confidence` parameter and `path_is_structural` diagnostic
- Mirror `code_callhierarchy`'s `suggestions` array in `code_definition`'s not-found response so operators get near-symbol candidates via the same shape across both tools
- Extend generated-code classifier to recognize `*.gen.{ts,tsx,js,jsx}`, `*.generated.{ts,tsx,js,jsx}`, `__generated__/`, and `.generated/` JS/TS conventions (e.g., TanStack Router, GraphQL Code Generator)
- Add `heuristic_import_no_matches` diagnostic on `code_impact(path=...)` for TS when path-mode resolves to no graph matches, distinguishing "no callers" from "import-resolver gap"
- Rewrite seed-211 fallback rule from a static language list to a response-shape condition so new languages benefit without seed edits
- Exclude the entire `.wavefoundry/` folder from graph indexing in downstream consumer projects so wavefoundry's own framework scripts no longer pollute consumer-project graphs (escape-hatched via `project_include_prefixes.code` for this self-hosting repo)
- Dispatch `notifications/resources/updated` for `wavefoundry://graph/*` URIs after auto-rebuild and after explicit `wave_index_build(content='graph')` so spec-conformant MCP clients invalidate cached graph-resource reads without operator action
- Add distinct dashboard node-kind colors for `package` and `namespace` so directory-aggregated package nodes are no longer indistinguishable from `external::*` greys

---

## 1.3.4 — 2026-06-01

Lifecycle-ID and build-suffix encoding rewrite. The prior scheme appended `BASE36[elapsed_minutes % 36]` as the 5th char of the lifecycle prefix and took the rightmost 4 chars as the build suffix — both wrapped every 36 minutes, causing lex order to disagree with wall-clock order. Three same-day 1.3.2 builds shipped within 27 minutes demonstrated the failure (`upgrade_wavefoundry` lex-selected the oldest one).

### Changes

- Replace lifecycle prefix encoding with integer-packed `(days_since_epoch * 288 + bucket_5min) mod 36^5`, base36 right-padded to 5 chars. 5-minute buckets (288/day) align cleanly with whole-minute AND whole-second boundaries and divide 36^5 with zero wasted slots. Lex order matches wall-clock within a 209,952-day (~575-year) horizon
- Build suffix is now the last 4 chars of the lifecycle prefix — single source of truth. Last-4-chars truncation is mathematically equivalent to packing with `mod 36^4`, giving a 5,832-day (~15.97-year) lex-monotonic horizon
- Shift project epoch from `2020-08-24` to `1999-05-01` so today's first new ID under the integer-packed scheme lex-sorts past the historical max real ID (`1p0r6` at 2,846,994). New IDs today begin at `1p2g0`
- Update `docs/workflow-config.json` lifecycle_id_policy: new `epoch_utc`, new `time_unit: "5-minute-bucket"`, new `buckets_per_day: 288`, expanded `notes` documenting the encoding

---

## 1.3.3 — 2026-06-01

Same-day patch covering description-refresh propagation, two graph-query polish fixes, and the wave 131bu close-out. Bumped from 1.3.2 because semver comparison strips build metadata; a same-version republish would have been invisible to `wave_upgrade` and left operators stuck on the prior build.

### Changes

- Detect tool-description changes during `wave_mcp_reload` and explicitly send the MCP `notifications/tools/list_changed` protocol notification so conformant clients re-fetch and surface the new descriptions automatically (FastMCP's `add_tool`/`remove_tool` do not send this automatically); response carries `description_changed_tools` + `tool_list_changed_notification_sent`; structured diagnostic explains success or failure path
- Alias `<file_id>::<class_name>` queries to the file id when the file is a class/module-merged node — operators querying with explicit qualification no longer hit `graph_symbol_not_found` for merged classes
- Tie-break `code_graph_path` BFS candidates on confidence: `RECEIVER_RESOLVED` / `CONSTRUCTION_RESOLVED` paths surface before `EXTRACTED` import placeholders when both reach the destination in the same hop count
- Update `seed-160` upgrade workflow to document the notification-based description-refresh path (no operator action required when conformant clients honor `tools/list_changed`; full restart remains the fallback when they don't)

---

## 1.3.2 — 2026-06-01

Patch on 1.3.1's ERROR-wrapped class declaration recovery. Field validation against the actual Solaris repository showed 1.3.1's recovery predicate accepted only `type_identifier` children — tree-sitter-swift's grammar-recovery state emits the class name as `simple_identifier` in practice, so the predicate silently missed every production ERROR-wrapped class. The graph rebuilds automatically on the first query after upgrade.

### Changes

- Broaden ERROR-wrapped class recovery predicate to accept `simple_identifier` and `identifier` children alongside `type_identifier` (tree-sitter grammars relabel the class-name node kind in their recovery state)
- Add child-text name-match as the second gate replacing the prior child-kind-presence-only check — keeps false-positive surface narrow even with the broader child-kind acceptance
- Extend recovery source-text prefix slice from 256 to 512 bytes to cover ERROR nodes whose modifier prefix runs longer than the prior bound

---

## 1.3.1 — 2026-06-01

Field-feedback patch covering one Swift attribution edge case and one cross-tool documentation gap. The graph rebuilds automatically on the first query after upgrade.

### Changes

- Recover ERROR-wrapped top-level class declarations in graph-builder definition walk so cross-file construction edges still resolve when tree-sitter wraps a class declaration in ERROR due to a parse failure deep in the class body (Swift, Kotlin, Scala, Java, C# — file-level-type languages)
- Document `CONSTRUCTION_RESOLVED` confidence value on `code_impact` response shape alongside `RECEIVER_RESOLVED` and `EXTRACTED`

Full per-change docs: `docs/waves/131bt field-feedback-round-3/1319v-bug error-wrapped-class-declaration-recovery.md` in the wavefoundry repository.

---

## 1.3.0 — 2026-06-01

Cross-language graph-builder precision improvements, new query-time aggregation, and upgrade-lifecycle automation. The graph rebuilds automatically on the first query after upgrade; MCP tool descriptions and parameter signatures refresh via `wave_mcp_reload` followed by a client reconnect (`/mcp` in Claude Code).

### Changes

- Resolve receiver types via type annotations in TypeScript, Python, PHP, and JavaScript (JSDoc); annotated declarations route to the correct method node, unannotated falls back to standard attribution
- Route construction-call edges to the class node across 11 languages: `new Foo()` in Java/C#/TypeScript/JavaScript/PHP, bare-call `Foo()` in Swift/Python/Kotlin/Scala, `Foo.new` in Ruby, struct-literal `Foo { x: 1 }` and `Foo::new()` in Rust, composite-literal `&Foo{}` and `new(Foo)` in Go
- Add `CONSTRUCTION_RESOLVED` confidence tag on construction-routed edges, peer-level to `RECEIVER_RESOLVED`
- Extend single-dominant-class merge to Python, JavaScript, TypeScript with dominance gate; add kebab-to-PascalCase basename matching for JS/TS
- Add `collapse_package_to_directory: bool` parameter to `wave_graph_report` covering Go, Python, Java, Kotlin, C#, Scala, PHP, Swift; produces `package` / `namespace` nodes per language idiom
- Hot-reload MCP tool schemas via `wave_mcp_reload`; parameter and description changes land in-process without a server restart
- Auto-rebuild stale graph synchronously on first query when the on-disk builder version is behind runtime; structured `graph_auto_rebuilt` diagnostic surfaces in the response
- Sync MCP tool descriptions for `wave_index_build`, `wave_index_health`, `wave_graph_report`, `code_impact`, `code_callhierarchy`, `code_graph_community` with shipped capabilities; restructure related seed-211 guidance
- Document client-side confidence filtering for refactor-safety and security-review workflows
- Rename release notes to `CHANGELOG.md` and relocate to `.wavefoundry/CHANGELOG.md` (project-level path; upgrade prunes the old `.wavefoundry/framework/RELEASE_NOTES.md` automatically); cumulative narrative format, no build-number structure, deliberately not Keep-a-Changelog

Full per-change docs: `docs/waves/131bt field-feedback-round-3/` in the wavefoundry repository.

---

## 1.2.1 — 2026-06-01

Operator field-feedback follow-on across two iteration rounds. Eliminate phantom call edges at index time, decompose collision diagnostics, broaden cross-language coverage for class/module merge and receiver-type resolution.

### Action required on upgrade

Rebuild the graph index once after upgrade: `wave_index_build(content='graph')`.

### Changes

- Move Java receiver-type resolution into the graph builder; eliminate phantom `calls` edges at index construction time so `code_impact` and `code_callhierarchy` return consistent results
- Decompose `name_collision_count` into `same_name_node_count`, `cross_file_collision: bool`, and `external_name_collision_count` (deprecated alias preserved one release)
- Curate per-language stdlib allowlist for `external_name_collision_count` across Java, C#, Kotlin, Swift, Python, JavaScript, TypeScript, Go, Rust, Scala, PHP, Ruby
- Split `file_hubs` section out of `chokepoints` on `wave_graph_report` so function-level rankings stay pure
- Add `community_size_class` (`small` / `medium` / `large` at <50 / 50–200 / 200+ thresholds) and `large_community_advisory` to `code_graph_community` responses
- Add stable `community_hub_node_id` anchor for community references (survives re-clustering across rebuilds)
- Add `collapse_class_module_pairs: bool` query-time view to `wave_graph_report` merging Swift file-and-class pairs
- Document and lock module fan-out semantics in `wave_graph_report` with a regression test
- Add empty-section diagnostic fields (`*_candidates_total`, `*_threshold`) to `chokepoints`, `file_hubs`, `orphan_docs`, `cross_layer` so `[]` distinguishes "no data" from "no hits"
- Surface graph rebuild discoverability on `wave_index_health` (per-layer `graph.last_built_at` / `node_count` / `edge_count`) and on `wave_index_build` responses (`graph_rebuilt` field + clarifying notice when `content` is not `graph`)
- Fix module-node simple-name extraction (basename without extension instead of bare extension)
- Merge Swift file-and-class nodes at the graph builder when the basename matches a top-level type declaration; extend to Java, Kotlin, C#, JavaScript, TypeScript, Scala, PHP, Rust (snake-to-PascalCase), Ruby (snake-to-PascalCase)
- Extend graph-builder receiver-type resolution to Kotlin, C#, Swift, Go, Rust, Scala
- Bundle a fix for the cross-file resolution `qualified_index` duplicate-suffix bug discovered during the receiver-type rollout

Full per-change docs: `docs/waves/13129 graph-tools-field-feedback-round-2/` in the wavefoundry repository.

---

## 1.2.0 — 2026-06-01

Initial graph tools field-feedback delivery from Solaris (Swift) and Aceiss (Java) tier-1 and tier-2 reports.

### Action required on upgrade

Rebuild the indexes after upgrade.

### Changes

- Add question-type pattern library covering navigational, explanatory, and instructional queries in the guru seed
- Improve graph tool shape consistency: dual community return on `code_impact`, pagination, per-hop attribution, communities overview
- Add generated-code classifier for Java and C# (header detection, path heuristics, `.gitattributes` opt-in) with `exclude_generated` filter and collapse mode
- Add AOP/advice empty-incoming detection (`caller_pattern: "advice"`) for Java and C# attribute annotations
- Classify Java `method_reference` (`Foo::bar`) as call sites
- Enable Kotlin reference resolution end-to-end
- Add `name_collision_count` diagnostic, `betweenness_computed` field, large-community `pagination_hint`, and `exclude_external` filter to `wave_graph_report`
- Add Java receiver-type filter at `code_callhierarchy` query time (promoted to graph builder in 1.2.1)

Full per-change docs: `docs/waves/130rj graph-tools-field-feedback-tier-1-and-2/` in the wavefoundry repository.

---

## 1.1.0 — 2026-05-31

Graph index extraction and clustering, graph-backed MCP query surface, refresh-and-instruct unification across graph tools, dashboard graph visualization.

### Action required on upgrade

Build the graph index once: `wave_index_build(content='graph')`.

### Changes

- Build per-layer code/doc graph during indexing with `defines` / `imports` / `calls` / `doc_references_*` edges; reverse invalidation prunes stale edges on file delete or rename
- Cluster the graph into communities via Leiden with label-propagation fallback
- Switch indexer to incremental chunk-delta embedding; force full LanceDB rebuild when `chunk_hash` is missing
- Centralize workflow-config include-prefix reading in the indexer; drop redundant forwarding from post-edit hook, dashboard, and server background paths
- Add `code_graph_path`, `code_graph_community`, `code_graph_status` MCP tools and `wavefoundry://graph/*` resources
- Add `direction=forward|backward|either` to `code_graph_path`
- Add graph-narrowed `code_definition` with incremental refresh; cold lookups drop from 38–43 s to sub-300 ms
- Flip graph augmentation default to on for `code_keyword`, `code_search`, `code_definition`, `code_references`
- Wire refresh-and-instruct uniformly across `code_references`, `code_callhierarchy`, `code_callgraph`, `code_impact`, `code_graph_path`, `code_graph_community`, `wave_graph_report`
- Consolidate graph-degradation diagnostic vocabulary to `graph_index_missing_degraded` / `graph_not_ready` / `graph_symbol_not_found`
- Add dashboard graph visualization, community overview, diff view, and index/graph status tiles; reorder Agents panel above Graph; remove breadcrumb back arrow and view-mode pills
- Modal dialogs own Escape key instead of the graph back handler
- Ignore `.wavefoundry/` runtime lock files via gitignore and rendered `.aiignore`
- Anonymize council synthesis output; enforce prepare-phase council-verdict recording
- Encode fix-now-not-later default in review-seat seeds (~20 LOC threshold; per-finding justification required when routing to follow-on)

Full per-change docs: `docs/waves/12xr1`, `12xr2`, `12xr3`, `1304x`, `1305t` in the wavefoundry repository.

---

## 1.0.1 — 2026-05-26

Patch release with test runner fix, search heuristics canonicalization, and README refresh.

### Changes

- Fix test runner single-run guard to prevent duplicate test execution
- Canonicalize search retrieval heuristics across `code_search` and `code_keyword`
- Refresh README with current operator orientation
- Strengthen test_run_tests_cache lifecycle assertions

Full per-change docs: `docs/waves/0rld3`, `0rld5` in the wavefoundry repository.

---

## 1.0.0 — 2026-05-24

Initial semver release. Python tool venv, venv-aware launcher shims, framework_revision manifest contract.

### Changes

- Adopt semver versioning for the framework with stamped `.wavefoundry/framework/VERSION`
- Introduce Python tool venv at `~/.wavefoundry/venv` for isolated dependencies
- Add venv-aware launcher shims under `.wavefoundry/bin/` for setup, docs-lint, docs-gardener, mcp-server, update-indexes, upgrade-wavefoundry, wave-dashboard, wave-gate
- Establish `framework_revision` contract in `docs/prompts/prompt-surface-manifest.json` aligned with the stamped VERSION

Full per-change docs: `docs/waves/12tms` in the wavefoundry repository.

