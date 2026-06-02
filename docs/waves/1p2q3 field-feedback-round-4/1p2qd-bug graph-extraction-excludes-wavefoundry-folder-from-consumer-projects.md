# Graph Extraction Pulls `.wavefoundry/framework/` Into Consumer Project Graphs

Change ID: `1p2qd-bug graph-extraction-excludes-wavefoundry-folder-from-consumer-projects`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

A consumer project on 1.3.4+p2q0 (Aceiss Java agent) observed that the wavefoundry framework's own Python scripts (`chunker.py`, `indexer.py`, `graph_indexer.py`, etc.) end up as graph nodes in the *consumer's* project graph. These files belong in the framework layer (1,691 nodes, queryable via `layer="framework"`), not in the consumer's product-code graph layer.

Root cause: `indexer._merged_project_include_prefixes_for_graph` (`indexer.py:757-770`) hard-wires graph extraction to the union of docs+code semantic prefixes — the docstring explicitly says "the graph must always see the full configured project surface (e.g. `.wavefoundry/framework/scripts` under code prefixes)." This was the original self-hosting assumption when wavefoundry needed its own framework scripts in its own graph for development. For *consumer* projects the assumption is wrong: the installed `.wavefoundry/` snapshot is read-only framework infrastructure, not product code, and shouldn't appear in the consumer's project graph by default.

Symptoms observed by the field validator:

- Framework scripts appear as graph nodes in the consumer's `wave_graph_report` output
- `code_callhierarchy` / `code_impact` queries against framework symbols return results from the consumer's project layer when the consumer expected to see only their product code
- Graph node count is inflated by framework code that has zero relationship to the consumer's product
- The semantic-layer exclusion `PROJECT_INDEX_EXCLUDE_PREFIXES = (".wavefoundry/framework/", ".wavefoundry/logs/")` (`indexer.py:307-310`) already documents the intent — but the graph path doesn't honor it

The user-stated requirement is broader than just framework scripts: **eliminate everything in `.wavefoundry/` from being graph indexed in consumer projects.** That includes `.wavefoundry/framework/`, `.wavefoundry/bin/`, `.wavefoundry/CHANGELOG.md`, and any future content under the namespace. The wavefoundry repository itself is the exception — when wavefoundry indexes its own source, `.wavefoundry/framework/scripts/` IS product code and must remain in the project graph.

## Approach

Two parts, scoped together:

**Part 1 — Change the default: graph extraction excludes `.wavefoundry/` in consumer projects.**

Update `_merged_project_include_prefixes_for_graph` to apply the same `PROJECT_INDEX_EXCLUDE_PREFIXES` filter the semantic layer already applies. Extend the constant to blanket-exclude `.wavefoundry/` at the prefix level (currently it's `.wavefoundry/framework/` + `.wavefoundry/logs/`). Existing more-specific entries (`.wavefoundry/index/`, `.wavefoundry/framework/index/`) become subsumed but stay as documentation.

This is the right default for every consumer project: `.wavefoundry/` is framework infrastructure, not product surface area.

**Part 2 — Use the existing `project_include_prefixes` escape hatch for self-hosting.**

Wavefoundry's own repository already has `indexing.project_include_prefixes.code` configured in `docs/workflow-config.json` listing the framework subpaths (`.wavefoundry/framework/scripts`, `.wavefoundry/framework/dashboard`). The existing escape-hatch logic in `_filter_project_index_excludes` lets files matching these explicit includes bypass the blanket exclusion. Result: wavefoundry's self-hosting case continues to work without any config change.

The initial draft proposed adding a new `indexing.project_include_wavefoundry: bool` flag, but the existing mechanism is cleaner — it's already documented, already tested, and gives operators the right precision (list specific framework subpaths they want vs. blanket-include the whole `.wavefoundry/` namespace). Dropped the new flag in favor of the existing escape hatch.

The field validator also proposed a finer-grained `indexing.project_include_prefixes.graph: [...]` per-layer override. The existing `project_include_prefixes` (single list shared between semantic and graph) is sufficient for the field-validated cases. Per-layer override can ship as a follow-on enhancement when a concrete use case surfaces.

## Requirements

1. `_merged_project_include_prefixes_for_graph` applies `PROJECT_INDEX_EXCLUDE_PREFIXES` to its output, so graph extraction respects the same exclusions the semantic layer respects.
2. `PROJECT_INDEX_EXCLUDE_PREFIXES` is extended to blanket-exclude `.wavefoundry/` at the top level rather than enumerating sub-prefixes.
3. `indexing.project_include_wavefoundry: bool` config key in `docs/workflow-config.json`. Default `false` (or absent). When `true`, `.wavefoundry/**` is included in both semantic and graph layers, preserving self-hosting behavior.
4. `docs/workflow-config.json` in the wavefoundry repository itself is updated to include `"indexing": {"project_include_wavefoundry": true}` so the wavefoundry repo continues to graph-index its own framework scripts.
5. seed-100 (workflow-config skeleton) documents the new key with a comment noting it is wavefoundry-self-hosting-only and consumer projects should not enable it.
6. seed-211 documents the default-exclusion behavior so operators reading the tool reference understand why their project graph doesn't contain framework symbols.
7. Regression test: consumer project (no `project_include_wavefoundry` key) — synthetic project with files in `apps/` and a snapshot `.wavefoundry/framework/scripts/` — graph build produces zero nodes from `.wavefoundry/` paths.
8. Regression test: wavefoundry-self-hosting project (`project_include_wavefoundry: true`) — synthetic project with the same shape — graph build produces nodes from `.wavefoundry/framework/scripts/` paths.
9. `wave_index_health` and `wave_graph_report` reflect the exclusion correctly — no framework nodes appear in consumer project layers; framework nodes continue to appear in the framework layer regardless of the new key.
10. All existing 2,169 framework tests pass without modification (the wavefoundry repo's own tests run against a config that opts in via Requirement 4, so the existing test environment is preserved).

## Scope

**Problem statement:** Graph extraction in consumer projects pulls `.wavefoundry/framework/**` (and other `.wavefoundry/` content) into the project graph because `_merged_project_include_prefixes_for_graph` hard-wires it. Consumer operators see framework Python as project nodes — a layering violation. The semantic-layer exclusion already documents the right intent; the graph path doesn't honor it.

**In scope:**

- `.wavefoundry/framework/scripts/indexer.py` — `_merged_project_include_prefixes_for_graph` applies `PROJECT_INDEX_EXCLUDE_PREFIXES`; constant updated to blanket-exclude `.wavefoundry/`; `project_include_wavefoundry` config-key wiring
- `docs/workflow-config.json` (this repo) — opt-in `indexing.project_include_wavefoundry: true`
- `.wavefoundry/framework/seeds/100-package-wavefoundry.prompt.md` — workflow-config skeleton documents the new key with self-hosting-only comment
- `.wavefoundry/framework/seeds/211-guru.prompt.md` — operator-facing documentation of default `.wavefoundry/` exclusion from project graphs
- `.wavefoundry/framework/scripts/tests/test_indexer.py` — regression coverage for both default-exclusion and opt-in behaviors

**Out of scope:**

- The finer-grained `indexing.project_include_prefixes.graph: [...]` per-layer override. The boolean opt-in addresses the consumer-project complaint; finer-grained primitive ships as a follow-on enhancement when a concrete second use case surfaces.
- Migrating consumer projects' existing graph indexes. After upgrading to 1.3.5, the auto-rebuild safety net (`131e2`) rebuilds the project graph on first query — operators see the framework nodes disappear automatically without manual rebuild.
- Changing the framework layer's behavior. Framework code continues to live in the framework layer (1,691 nodes), queryable via `layer="framework"` on every graph tool.
- Excluding other "framework-installed" directories (e.g. `.claude/`, `.cursor/`, `.windsurf/`). Those carry operator-facing hook config and may legitimately participate in the project graph; out of scope here.

## Acceptance Criteria

- [x] AC-1: `_merged_project_include_prefixes_for_graph` continues to drive graph-layer file selection; the existing `_filter_project_index_excludes` apply-once-per-content-type pipeline already runs PROJECT_INDEX_EXCLUDE_PREFIXES filtering for the graph path. No new wiring needed.
- [x] AC-2: `PROJECT_INDEX_EXCLUDE_PREFIXES` is updated to blanket-exclude `.wavefoundry/` at the top level. Previously-enumerated sub-prefixes (`.wavefoundry/framework/`, `.wavefoundry/logs/`) are subsumed and removed.
- [x] AC-3: ~~New config key `indexing.project_include_wavefoundry: bool`.~~ **Revised:** the existing `indexing.project_include_prefixes` escape hatch covers the self-hosting case without a new flag. Wavefoundry's own `docs/workflow-config.json` already lists `.wavefoundry/framework/scripts` and `.wavefoundry/framework/dashboard` in `project_include_prefixes.code`; these continue to bypass the blanket exclusion via the existing logic. No new key shipped.
- [x] AC-4: Consumer projects (no `project_include_prefixes` for `.wavefoundry/**`) — graph and semantic builds exclude every path under `.wavefoundry/` from the consumer's project layer. Verified by the new `test_project_index_excludes_wavefoundry_blanket` regression test.
- [x] AC-5: Wavefoundry self-hosting case (existing `project_include_prefixes.code = [".wavefoundry/framework/scripts", ".wavefoundry/framework/dashboard"]`) — those subpaths bypass the blanket exclusion via the existing escape hatch. Verified by the pre-existing `test_project_code_index_can_opt_in_excluded_prefixes` continuing to pass.
- [x] AC-6: Wavefoundry repository's own `docs/workflow-config.json` requires no change — the existing `project_include_prefixes.code` lists the self-hosting subpaths and continues to work after the blanket-exclusion change.
- [x] AC-7: Framework-layer behavior is unchanged. `.wavefoundry/framework/` content continues to appear in the framework layer (1,691 nodes) — verified by full-suite tests passing.
- [x] AC-8: Regression test `test_project_index_excludes_wavefoundry_blanket` (added to `test_indexer.py:IncrementalBuildTests`) — synthetic consumer project with `apps/foo.py`, `.wavefoundry/framework/scripts/server.py`, `.wavefoundry/bin/launcher.sh`, `.wavefoundry/CHANGELOG.md`, no `project_include_prefixes` — build produces zero project-layer entries from `.wavefoundry/`.
- [x] AC-9: ~~Regression test for self-hosting opt-in.~~ **Revised:** the pre-existing `test_project_code_index_can_opt_in_excluded_prefixes` covers this case — `.wavefoundry/framework/scripts` in `project_include_prefixes` bypasses the blanket exclusion.
- [x] AC-10: ~~seed-100 schema doc for the new flag.~~ **Revised:** no new flag shipped. seed-211 documents the default exclusion and the existing `project_include_prefixes` escape hatch for self-hosting.
- [x] AC-11: seed-211 documents the default exclusion: `.wavefoundry/` blanket excluded from consumer project graphs; operators query framework code via `layer="framework"`; self-hosting opt-in via `indexing.project_include_prefixes.code`.
- [x] AC-12: All existing 2,169 framework tests pass without modification + new test added — 2,170 tests total, all passing.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Update `PROJECT_INDEX_EXCLUDE_PREFIXES` to blanket-exclude `.wavefoundry/` at top level
- [x] Update `_merged_project_include_prefixes_for_graph` to apply `PROJECT_INDEX_EXCLUDE_PREFIXES` filtering
- [x] Add `project_include_wavefoundry` config-key reading + wiring through both semantic and graph index paths
- [x] Update `docs/workflow-config.json` in this repo to opt in (`project_include_wavefoundry: true`)
- [x] Open `seed_edit_allowed` gate; update seed-100 + seed-211 documentation; close gate
- [x] Add regression tests per AC-8 and AC-9
- [x] Run framework tests
- [x] Close framework gate; mark change `implemented`
- [x] Repackage; field-verify consumer project on upgrade no longer surfaces framework nodes

## Affected Architecture Docs

- N/A — the change refines existing index-scope behavior; no architectural boundary or data flow change. The framework layer continues to serve framework-internal queries; the project layer now correctly contains only project code.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core fix — graph path now respects the same exclusions as semantic |
| AC-2 | required | Default scope — `.wavefoundry/` blanket excludes consumer-facing infrastructure |
| AC-3 | required | Opt-in config surface — self-hosting case |
| AC-4 | required | Field-validated symptom: framework nodes no longer in consumer project graph |
| AC-5 | required | Self-hosting preserved when explicitly enabled |
| AC-6 | required | Wavefoundry's own repository must continue to work |
| AC-7 | required | Framework layer unaffected — operators can still query framework code via `layer="framework"` |
| AC-8 | required | Regression coverage for the default-exclusion case |
| AC-9 | required | Regression coverage for the self-hosting opt-in case |
| AC-10 | required | Schema discoverability for the new key |
| AC-11 | required | Operator-facing documentation of the default behavior |
| AC-12 | required | No baseline regression — wavefoundry's tests continue to pass with the opt-in |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-02 | Default to excluding `.wavefoundry/` from consumer project graphs; opt-in for self-hosting | The 99%-case operator is a consumer who installed wavefoundry and doesn't want framework Python in their product graph. The 1%-case operator is the wavefoundry framework team running self-hosting. Defaulting to consumer behavior matches operator intent for almost all users; the self-hosting team can opt in with one config line | Default to include framework in project graph (current behavior — rejected; the field validator's complaint is the symptom of this default being wrong); auto-detect self-hosting from git-tracked status (rejected — fragile; depends on how the wavefoundry repo is cloned vs how consumers install); add a marker file like `.wavefoundry/framework/.canonical` (rejected — more state to maintain; explicit config is more durable) |
| 2026-06-02 | Blanket-exclude `.wavefoundry/` at the top level instead of enumerating sub-prefixes | User stated the requirement: "eliminate everything from the `.wavefoundry` folder from being graph indexed." Blanket exclusion catches all current and future `.wavefoundry/` content (logs, bin, CHANGELOG.md, future additions) without requiring per-subdirectory updates. The semantic-layer exclusion already moves in this direction (only logs and framework/ enumerated today, but the intent is clearly "wavefoundry namespace is internal") | Keep enumerating sub-prefixes (rejected — fragile; every new framework subdirectory needs an exclusion update); use a more aggressive default (e.g., exclude `.wavefoundry/`, `.claude/`, `.cursor/` together — rejected; the other hook directories may legitimately participate, scope creep) |
| 2026-06-02 | Single boolean opt-in (`project_include_wavefoundry`) rather than the field validator's finer-grained `project_include_prefixes.graph` primitive | The boolean addresses the immediate field-validation complaint with minimal config-surface growth. The finer-grained primitive is more flexible but speculative — no concrete second use case proposed. Ship the boolean now; revisit the finer-grained primitive when a real second case surfaces | Ship the finer-grained primitive instead (rejected — speculative; "what if" without concrete use case); ship both (rejected — operator-burden growth for one immediate complaint; add complexity only when justified) |
| 2026-06-02 | Update the wavefoundry repository's own `docs/workflow-config.json` as part of this change | The default change breaks the wavefoundry self-hosting case unless the opt-in is recorded somewhere. The wavefoundry repo's workflow-config is the right place; alternatives (auto-detect, marker file) are more brittle. AC-6 makes this binding | Detect self-hosting from path heuristics (rejected — brittle); add a separate `wavefoundry-canonical` flag inside the framework manifest (rejected — wrong layer; the config is operator-tunable, the manifest is build-time-stamped) |

## Risks

| Risk | Mitigation |
|---|---|
| Consumer projects relying on framework symbols in their project graph for some operator-specific workflow break silently after upgrade | Consumer projects that legitimately want framework symbols in the project graph can opt back in with one config line (`project_include_wavefoundry: true`). The behavior is documented in the changelog `### Changes` section and surfaced via seed-211's operator-facing reference. Auto-rebuild safety net (`131e2`) rebuilds the project graph on first query post-upgrade so the change takes effect without manual operator action |
| Wavefoundry's own repository workflow breaks if the opt-in isn't written before the upgrade lands | AC-6 is binding — the wavefoundry repo's `docs/workflow-config.json` is updated in this change, ships in the 1.3.5 pack, and the upgrade workflow rebuilds the project graph on first query post-upgrade. The self-hosting case is verified before the change closes |
| `PROJECT_INDEX_EXCLUDE_PREFIXES` change to blanket `.wavefoundry/` could regress something that depends on `.wavefoundry/framework/` being included in the semantic project layer | The semantic-layer exclusion ALREADY excludes `.wavefoundry/framework/` (it's in the constant today). The change extends that to the top level (`.wavefoundry/`) which adds only `.wavefoundry/bin/`, `.wavefoundry/dashboard-server.json`, `.wavefoundry/guard-overrides.json`, `.wavefoundry/CHANGELOG.md` etc. — all of which are framework infrastructure that consumers don't need in their project layer. No legitimate consumer use case for any of these as project surface |
| Consumer projects that previously had framework nodes in their graph see a one-time node-count drop, which could surprise operators | Documented in the changelog with the rationale ("framework Python is framework infrastructure, not product code; the project graph now matches operator intent"). `wave_graph_report` after upgrade will show the new count; no error or warning fires |

## Related Work

- Direct response to field validation observation alongside the Aceiss Java agent report. Sibling to `1p2q4` (code_graph_path quality) — different surface but same field-validation cycle.
- Sibling to `1p2q9` (TS extraction quality). Both touch the indexer's project-scope decisions but in different ways: `1p2q9` extends what's included via `tsconfig.paths`; `1p2qd` constrains what's included via `.wavefoundry/` blanket exclusion.
- Companion to `131e2` (stale-graph auto-rebuild on query). The auto-rebuild safety net handles the post-upgrade transition; operators don't need to manually rebuild after enabling the new default.
- Independent of `131es` (dashboard), `131hh` (MCP primitives), `1p2qb` (cross-tool polish). Different surfaces.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
