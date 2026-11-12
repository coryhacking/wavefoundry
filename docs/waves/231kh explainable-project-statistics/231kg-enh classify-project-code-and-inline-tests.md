# Classify project code and inline tests

Change ID: `231kg-enh classify-project-code-and-inline-tests`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-11
Wave: 231kh explainable-project-statistics

## Rationale

Tensorwell reports Python build/qualification tooling labelled production, Rust inline tests counted as production, and evidence JSON mixed into data. Its rough 11,800-line inline-test estimate is not a parser result and is not an acceptance target. Current `_files` classifies whole files by path/name, `_code` calls every remaining code file production, and line counting is deliberately lexical. An executed control returned one build-script Python line and six Rust lines (including a cfg(test) module) as production, with zero test lines. This change addresses feedback items 1–4 while 231kf makes coverage and operational data explainable.

## Product Intent

A multi-language project's operator can distinguish declared shipped code, tooling, tests and evidence, see where that work lives, and identify inline Rust test code without mistaking a filename heuristic for delivery composition or test coverage. AC-1 through AC-4 establish this on controlled repositories; configured roles are project declarations, not proof of executable packaging. The adopted vision's Horizon 2 benefits from more accurate system understanding; this does not select new roadmap work or alter VISION.md.

## Requirements

1. **Explicit optional roles.** Add optional `statistics.path_roles` in `docs/repo-profile.json`: an array of `{path, role}` entries. Paths are normalized repository-relative literal file paths or directory prefixes ending in `/`; roles are `shipped`, `tooling`, `test`, `evidence`, `generated`. The longest matching literal path wins; duplicate equal paths with conflicting roles are invalid. Reject absolute paths, parent traversal and malformed entries with a fixed statistics-configuration reason; never execute patterns or read outside the root. Mappings classify already eligible files and cannot widen the indexer's walk or override exclusions. No profile or no matching entry keeps an explicit inferred `non_test`/`test` fallback. An agent may propose roots from an Implementation guard, but stats never interprets AGENTS.md or writes mappings automatically. Project profiling/re-profiling must preserve existing `statistics.path_roles` unless the operator explicitly directs a change; update the profile-authoring guidance accordingly.
2. **Separate format, role and test extent.** Preserve code/documentation/data categories and language totals. Add role breakdowns with stated provenance (configured or inferred); `evidence`/`generated` do not silently disappear from repository totals. The `evidence` role requires an explicit mapping for files already eligible for the walk. Do not infer it from lifecycle folders or path names. Pruned lifecycle evidence folders remain excluded and are reported by 231kf as counted policy exclusions, not zero-valued evidence-role contents. An explicit evidence mapping cannot restore a pruned file. Expose unmatched-role counts. “Shipped” describes declared path responsibility, not a packaged-binary census. Inline test extent is a second dimension: show non-test and test code within a role so an entire source file's shipped designation does not pretend its test module ships. File totals remain unique; mixed-file counts are labelled and never summed as disjoint files.
3. **Compatibility and labels.** Keep schema-version-1 `production`, `test` and `test_code_ratio` fields with their existing path-based meanings as compatibility fields, accompanied by a legacy-method note. Add effective test/non-test line counts and their ratio for the improved view; do not silently repurpose old JSON keys. Human reports use “non-test” for an unconfigured non-test bucket, never “production” as a shipping claim, and use the new effective breakdown when available. The total remains the same lexical code-line universe: effective test plus non-test equals combined code lines. Test share is not test coverage. Documentation/data are not made code by role mappings.
4. **Rust inline tests.** Use the repository's available syntax parser to identify complete item spans gated by the syntax-equivalent `#[cfg(test)]` attribute (allowing whitespace through the parsed syntax), including modules, and exact `#[test]` function items. Count the union of recognized spans once; exclude similarly spelled strings/comments and preserve non-test items after a module. Attribute lines belong to their item. A whole-file test path remains wholly test. No macro expansion, arbitrary cfg-expression evaluation, compiler invocation or guessed span-to-EOF. Detected unsupported conditional forms, unavailable parser or parse errors must disclose an unknown/partial inline-analysis state; macro-generated test semantics are not discoverable without expansion and receive a general coverage limitation, not a promise to identify every hidden test. Retain a labelled path-only fallback instead of claiming zero inline tests or exact effective totals. Existing lexical comment rules remain visible.
5. **Swift test targets.** Preserve existing filename/directory heuristics and support nonstandard Swift test-target roots through explicit `test` path roles. Document mapping the project's known target roots into that configuration; no execution of Package.swift, Xcode project generation, compiler or package manager. Automatic semantic inference of arbitrary Swift build manifests is out of scope, and the report states that boundary.
6. **Optional directory view.** Add `group_by="directory"` to the shared collector/MCP surface and `--group-by directory` to CLI; omission preserves the default view, and other values return invalid arguments. When the code section is requested, return top-level directory (root files use `.`) and language rows with unique files and the same line/role/test methods as the main code section. Sum rows to the same included-file totals; collect no files or parse code when code/TODO sections are not requested. Reuse the single collected file set and counts, not a second walk. Do not create new aggregates in the skill.
7. **Delivery.** Extend the shared statistics payload and formatter, MCP/CLI signatures, skill registry and generated skills, profile configuration documentation and source examples. Preserve section isolation, current scope exclusions, no network/subprocess/model load, bounded file size, renamed-profile nouns/roots, and existing dashboard calculations. Role configuration is read-only during reporting. Do not add parser packages or change source-index/chunker eligibility to implement this feature. The implementer records parser availability and precision limits rather than silently expanding language scope.

## Scope

**In scope:** `project_stats.py`, existing parser helper usage, `wf_server/server_impl.py`, `wf_cli.py`, `render_agent_surfaces.py`, profile-authoring guidance and documentation/template if one exists, generated skills, public contract fixtures/tests, statistics spec and changelog. Use existing profile/root readers; add a small shared helper only if it prevents conflicting ownership.

**Out of scope:** actual Tensorwell/Waveforge configuration writes, parsing AGENTS.md as runtime configuration, executing build manifests, determining actual linker/package output, semantic line counting, macro expansion or arbitrary cfg evaluation, automatic Swift manifest execution, new external dependencies, dashboard redesign, additional directory depths or unrestricted glob engines. Protect Envision and lifecycle guidance, current local-build stamps and other waves.

## Acceptance Criteria

- [x] AC-1: A fixture with shipped Rust/Swift roots, Python tooling, tests, evidence and generated files produces exact configured/inferred role counts, provenance and unique totals. Longest-prefix precedence, conflicting duplicate paths, invalid/escaping paths, missing configuration and ignored paths are verified. The old “all non-test is production” report fails the intended display oracle while legacy JSON counters retain their old values.
- [x] AC-2: Real Rust parser fixtures with nested cfg(test) modules, exact test functions, ordinary items after the module, strings/comments resembling attributes, overlapping spans and whole-file test paths yield exact union-based test/non-test lexical line counts without duplicated files. Parser failure/unavailability and detected unsupported conditional cases report partial/unknown precision with labelled fallback; whitespace-equivalent attributes work, and macro-hidden tests carry an explicit general limitation without pretending to detect expanded semantics. The original path-only implementation fails the inline-test oracle.
- [x] AC-3: Nonstandard Swift target directories explicitly mapped to `test` are counted as tests; an unmapped production Swift directory stays non-test. No build manifest executes. An eligible JSON file explicitly mapped as evidence is separated by role while retaining its data category. Pruned evidence folders under default/renamed lifecycle roots remain outside role/file totals even with an explicit mapping; 231kf reports their observed policy exclusions. Equal-named eligible paths without mappings retain their inferred fallback. Category/language totals still reconcile.
- [x] AC-4: Public MCP and CLI directory requests return identical top-level/language totals that reconcile with the main code view, including root files and mixed test files. Default calls retain compatible fields; invalid grouping is rejected; requests without code/TODO avoid walking/parsing. The new view uses one file pass.
- [x] AC-5: Updated skill/CLI presentation uses effective counts and clear precision/provenance notes without calling non-test shipping or test share coverage; documentation names configuration and fallback behavior. Profile-authoring guidance requires preserving configured statistics roles during re-profiling; a seeded-profile preservation control verifies that a refresh retains those entries without operator direction to change them. Focused default and renamed-profile tests, parse-failure controls and unchanged legacy-contract fixtures pass. Native platform evidence is qualified honestly.

## Tasks

- [x] Define and validate explicit role configuration and preserve it during re-profiling; keep pruned evidence outside the counted file set.
- [x] Implement bounded Rust span analysis and Swift explicit test-root support; preserve legacy counters.
- [x] Add shared optional directory view and MCP/CLI/skill presentation.
- [x] Update profile/statistics documentation and focused public/parser/default/renamed tests; run applicable qualification and independent reviews.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Role/parser and directory reporting | implementer | 231kf | Shared statistics files are serialized |
| Verification | independent reviewers | implementation | Exact line-set and compatibility oracles |

## Serialization Points

- `.wavefoundry/framework/scripts/project_stats.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/wf_cli.py`, `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/tests/`, `docs/specs/mcp-tool-surface.md`, `docs/references/`

Depends on `231kf-enh explain-statistics-coverage-and-health` for its common report changes. Only implementer writes source; reviewers are read-only. Generated skills are rendered from the registry; no backing prompt is introduced.

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md` for profile/parser/read-only ownership and `docs/architecture/performance-budget.md` for one-pass bounded parsing. Document configuration in the maintained repo-profile reference and MCP tool specification.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Distinguishes declared product responsibility from filename inference |
| AC-2 | required | Corrects the motivating inline Rust misclassification with explicit limits |
| AC-3 | required | Supports multi-language/downstream target and evidence layouts |
| AC-4 | required | Makes composition visible without inconsistent duplicate counting |
| AC-5 | required | Preserves compatibility and truthful presentation |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-11 | Observe: implementation and independent delivery review complete; all ACs/tasks satisfied. Final reviewed-tree canonical suite passes 12,814 tests across 248 files, 12 reported skips, 863.764 seconds. | Current successful framework receipt; six required lane approvals and council establishes. One CLI path-display finding repaired and reverified. No native Windows/live downstream/human comprehension claim. |
| 2026-11-11 | Observe: parser reload integration now uses existing indexer-owned runtime; reload guard unchanged. Fixed new test paths to use profile roots. Intentional public contract fixtures updated only for wf_stats: two optional arguments in core/declared schema goldens and its handler digest. | 42 stats, 25 frozen golden and 27 registry tests pass; semantic fixture diff contains no other changed tool. Scanner runtime identity seam and canonical rerun pending. |
| 2026-11-11 | Observe: 42 focused report/public tests pass in 3.04 seconds; actual Rust parser ran without skips. Exact span union, mixed-file/role/directory totals, Swift explicit roots, default/opt-in MCP/CLI parity and section isolation verified. Source frozen for full qualification and fresh independent review. | `test_stats_roles`, `test_stats_explainability`, `test_stats_surfaces`, `test_project_stats`; mutants deleting traversal rejection, Rust spans, boolean validation and opt-in detail rejected by respective invalid-role, exact-span, default-detail and opt-in tests. No native Windows claim. |
| 2026-11-11 | Observe: amended seed030 executed by a fresh author on a disposable seeded Python CLI/library fixture. It refreshed project facts and repo-index while preserving all four original path_roles exactly, including absent paths. Coordinator independently compared the saved expected block to output. Skill surfaces regenerated from registry. | One bounded authoring replay under `.wavefoundry/work/231kh/profile-replay`; preserved shipped/tooling/evidence/test declarations; no claim of universal agent adherence. Canonical seed and generated stats skill retain instructions; final source tests/review pending. |
| 2026-11-11 | Readback: add explicit eligible-file roles, bounded Rust inline test spans and optional directory/language composition; preserve legacy path-only JSON counts while the human view uses effective non-test/test counts and precision limits. For example, a shipped Rust file may contain test spans without claiming those spans ship. Shared report files remain single-writer; seed030 preserves operator role mappings during profile refresh. | AC-1–5; project_stats/API/CLI, registry, profile-authoring seed, generated skills, docs and exact parser/public fixtures. No compiler, new parser dependency, widened walk or dashboard change. |
| 2026-11-11 | Amended R1/R2, AC-3/AC-5 and tasks after operator-approved review. | Explicit eligible evidence only; excluded folders stay excluded; profile preservation required. Focused readiness refresh pending. |
| 2026-11-11 | Planning only. Executed current `_code` on one Python build line and a six-line Rust file with cfg(test) module: production=1/6, tests=0/0. This proves existing whole-file accounting, not Tensorwell's rough 11,800-line estimate. | `project_stats._files`, `_code`; direct bounded Python control |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-11 | Remove inferred lifecycle evidence roles; retain explicit evidence roles for eligible files and preserve role mappings during re-profiling. | The existing walk prunes lifecycle evidence, so inferred counts cannot establish AC-3. 231kf reports those observed policy exclusions without widening scope. Prior readiness needs focused refresh. | Widening statistics scope or knowingly deferring an impossible AC. |
| 2026-11-11 | Explicit literal path roles plus bounded Rust syntax spans; retain compatibility counters. | Replay: Python build scripts become declared tooling, Rust test spans become visible without moving source, eligible explicitly mapped evidence remains counted but separated; pruned evidence stays excluded. This informs rather than enforces packaging; exact fixture totals and a later field report test usefulness. | Path-only relabeling cannot fix inline Rust tests. Full compiler/build analysis adds execution, dependencies and cost to a read-only overview. |
| 2026-11-11 | Swift nonstandard target roots are declared, not executed from build files. | Maintainers can reuse known roots without trusting arbitrary manifest code; explicit unknowns are preferable to guessed targets. | Running Swift/Xcode project discovery violates the existing no-subprocess contract. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Apparent exactness from unsupported Rust syntax | Exact supported attributes, union spans, parser/error/unsupported notes and labelled fallback |
| Compatibility counters conflict with new totals | Retain old fields explicitly as legacy, render effective fields, exact reconciliation tests |
| Role rules accidentally widen file scope or depend on fork names | Classify after shared walk; root-relative literal paths never override configured exclusions |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
