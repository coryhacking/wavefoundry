# Rust cross-module free-function call binding

Change ID: `20e13-bug rust-cross-module-call-binding`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-11
Wave: 20e38 rust-cross-module-binding

## Rationale

Resolve two legitimate cross-module calls reproduced in a compile-valid three-file Rust library: an alias imported with `use crate::left::ping as left_ping` and a direct `crate::right::ping()` invocation. Both callee nodes exist, but published calls remain external. Improve this bounded coverage while preserving conservative identity, stored call sites and incremental correctness; this is not complete Rust name resolution.

## Requirements

1. Preserve explicit paths on syntactically supported `crate::...::function(...)` calls and aliased imports targeting such paths. Supported targets are free-function definitions reached through indexed crate-root/module declarations, including file modules and inline module qualification. Derive the target set from declaration facts and complete paths, never leaf names alone.
2. Bind only when caller crate identity and the complete path establish one project free-function target. For an imported alias, additionally prove a visible, unique, unshadowed import at that invocation; otherwise refuse promotion. Function/block/module scopes, parameters and local or closure bindings must not borrow an import from another scope. Missing roots/modules/items, ambiguous ownership/path candidates, non-project imports and unsupported computed receivers remain external. Multiple crates must not cross-bind. Preserve associated/trait behavior without relaxing the global receiver-ownership guard.
3. Preserve stored invocation coordinates and repeated occurrences through extraction, resolution, publication and served incoming/outgoing graph responses. Promote only exact proven matches; unresolved results keep honest external provenance.
4. Incremental merges must equal a fresh full build after callee or module/crate topology changes even when caller source is unchanged. Build bounded lookup/context data once per merge, without per-edge source scans or additional upgrade reporting/indexing work.
5. Bump the graph builder version for changed semantics. Document the existing graph refresh/invalidation consequence and coverage limits, without an eager upgrade build or live consumer qualification claim.

## Scope

**Problem statement:** Explicit Rust crate paths do not bind to existing indexed free functions.

**In scope:** Rust extraction and shared full/incremental resolution, crate/module identity facts, published-response and incremental regression fixtures, builder invalidation, graph architecture and changelog.

**Out of scope:** Cargo/dependency discovery, macro expansion, arbitrary re-exports/globs, general `self`/`super` imports, runtime dispatch/type checking, complete Rust coverage, non-Rust semantic changes, response schema changes, live setup/indexes, consumer upgrade repair, package build, commit/push and closing this new wave.

## Acceptance Criteria

- [x] AC-1: A compile-valid multi-file fixture with same-named free functions binds an aliased crate import and a direct crate-qualified call to their respective definitions; published incoming/outgoing responses preserve expression-derived coordinates and repeated occurrences. Oracle: actual extraction, merge, SQLite publication and registered responses versus explicit fixture targets/source spans.
- [x] AC-2: Missing module/item facts, competing crate ownership/targets, non-project imports and unknown/computed receivers remain external. Imported aliases promote only with per-invocation visible, unique, unshadowed import proof; compile-valid local/closure/parameter shadows and imports confined to other scopes do not falsely bind. Existing associated/trait and owned-receiver controls retain targets. Oracle: explicit expected negative edges, source-grounded lexical fixtures and affected existing suites.
- [x] AC-3: Callee deletion/re-addition and module/crate topology-only updates re-resolve untouched callers identically to an independent full build, including stored sites. Oracle: normalized published full/incremental edge sets.
- [x] AC-4: Changed indexing uses merge-scoped bounded lookups, existing builder-version invalidation refreshes old semantics, and authored documentation accurately describes support/limits. Oracle: source inspection, targeted work-count/version checks and validation of this change's documents.

## Tasks

- [x] Capture compile-valid baseline and design published-response regressions.
- [x] Implement bounded Rust crate-path extraction and unique crate/module free-function binding with incremental invalidation.
- [x] Verify negative/provenance/compatibility and full/incremental controls; record meaningful deleted/loosened-guard mutants.
- [x] Bump graph builder version and update architecture/changelog without extra upgrade work.
- [x] Run focused and canonical qualification, full docs validation and receipt-required independent delivery review; consolidate evidence inline.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Readiness | coordinator and independent reviewers | — | Standard isolated primer, fixed seats, receipt-selected rotating seat and separate required lanes |
| Implementation | implementer/coordinator | current readiness | One writing owner; current-source fresh CLI |
| Delivery | independent reviewers and council-chair | qualification | Frozen packet, fresh context and complete sweep |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_rust_provenance.py`
- `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_quality_eval.py`
- `docs/architecture/graph-index-system.md`

Root CHANGELOG.md is prose context, not a path token. No seed/protected generated surface edits.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md`: crate identity/path resolution, incremental context invalidation, builder version and bounded coverage. No new evidence folder or architecture file.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Fix legitimate calls while retaining invocation truth |
| AC-2 | required | Prevent false targets and ownership claims |
| AC-3 | required | Preserve correctness after untouched-caller updates |
| AC-4 | required | Bound hot-path work and state invalidation/coverage honestly |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-11 | Local rustc compile passed; actual builder and registered callgraph keep both calls external despite existing nodes. No repository code edited. | /private/tmp/wf-rust-cross-module-baseline.py and .json; alias external::crate.left.ping, direct external::ping; stored invocation spans survive |
| 2026-10-11 | Observe: independent standard readiness Council and code/QA/architecture found one deduplicated ARCH-R1 alias-visibility gap; performance approved feasibility with merge-context work-count notes. Repair-start recorded before one bounded Req2/AC2 clarification; delivery follows the targeted receipt, which does not require delivery Council. | Typed events and /private/tmp/wf-20e38-readiness-results.json; no implementation edits; seven reviewed hashes unchanged |
| 2026-10-11 | Observe: focused independent code/QA/architecture reverifications completed ARCH-R1's plan repair; current four required lanes and Council readiness approved. Prepare succeeded and wave opened. | Typed current-receipt approvals; /private/tmp/wf-20e38-focused-readiness-results.json; no remaining readiness blocker |
| 2026-10-11 | Readback: bind explicit crate-relative and proven visible unshadowed aliased free-function calls to distinct indexed targets; retain foreign/shadowed/ambiguous calls as external, exact stored occurrences and full/incremental parity. Before: left/right calls external despite existing nodes. After: each proven call reaches its exact target. Change graph indexer, four declared graph test files, graph architecture and changelog; builder 56, no Cargo/global receiver/schema/live upgrade changes. Thought: scoped extraction facts and one merged lookup address identity without additional upgrade work. | AC-1–AC-4; current readiness; one generic implementer writing owner, frontier reasoning selected for AST/incremental ambiguity; coordinator integrates and fresh four lanes review delivery |
| 2026-10-11 | Observe: 17 Rust provenance tests pass, including actual published incoming/outgoing repeated sites and independent full/incremental equivalence after callee and topology changes. Local rustc compiled new repeated/inline, lexical shadow and module/type constructor compatibility fixtures. AC-1 and AC-3 marked from executed proof; final frozen qualification and guard mutants remain. | Implementer executed real-parser/SQLite/registered-response tests; no live consumer or complete Rust-coverage claim |
| 2026-10-11 | Landing proof: final seven scratch mutants produced named assertion failures, not errors: remove lexical-shadow or local-item refusal → test_alias_scope_shadow_and_external_import_refuse_local_twins; first ambiguous owner → test_multiple_crates_do_not_cross_bind_and_shared_ownership_refuses; omit topology invalidation → test_callee_and_topology_changes_reresolve_untouched_published_callers; allow leaf fallback → test_missing_ambiguous_and_non_free_targets_never_use_leaf_fallback; remove exact constructor lookup or type-name invalidation → test_cross_file_type_new_keeps_exact_constructor_and_incremental_identity. The provisional uppercase constructor carveout was removed in favor of exact context. | /private/tmp/wf-20e38-mutants.py and .log; 19 Rust provenance and 58 incremental tests pass; four fixture compilations pass |
| 2026-10-11 | Coordinator integration: original generic compile and explicit served target/span assertions pass (left target 74..85, right 87..107). Full docs validation caught a stale current-version numeral in docs/RELIABILITY.md; corrected 55→56 as a documentation-only erratum under the existing accurate-builder-docs obligation. No requirement, authority or source-path expansion. | /private/tmp/wf-20e38-root-current-baseline.json; source diff and git diff --check; docs validation rerun follows |
| 2026-10-11 | Final freeze: new strict override containment prevents escaped/absolute/portable drive paths becoming project targets. Its deleted guard fails test_module_path_overrides_refuse_escape_absolute_drive_and_backslash, giving eight final landed-guard mutants. Final Rust/incremental qualification 78 tests, zero skips; previous frozen indexer 555 and quality 105 passed before the containment-only fix. AC-2/AC-4 verified, builder 56 documented; canonical final-source qualification follows. | Final graph source SHA256 25d3c4c276e13e1aeb4714b4cc21130cf016d1ea3605e3f26625ce898f5afed3; /private/tmp/wf-20e38-mutants.py and .log; fresh-process frozen logs; actual runtime model identity unknown |
| 2026-10-11 | Observe/Reflect: bounded integration probes compiled cleanly but exposed false alias promotion for match-arm and conditional-pattern shadows. Reopened AC-2; recorded binding facts must cover those local scopes before invocation proof is valid. Stopped only the verified owned canonical runner and descendants (unique stdout log), with no green receipt claim. Thought: add scoped pattern facts and affected positive/else controls, then re-freeze and qualify. | Actual match and if-let Rust compile/parser/publication probes; implementation self-check before delivery review; interrupted /private/tmp/wf-20e38-canonical.log not qualification |
| 2026-10-11 | Pattern repair verified: 79 final affected tests pass, zero skips (Rust 21, incremental 58). Compile-valid Rust 2024 fixture asserts exact invocation spans across match guards/arms/siblings, conditional initializer/body/else, while-let, let-chain suffix and outer aliases. Five new deleted/loosened pattern guards fail test_pattern_bindings_refuse_alias_but_preserve_sibling_else_and_outer_sites, giving 13 final mutants with assertion failures/no errors. AC-2 reverified; source frozen for restarted canonical qualification. | /private/tmp/wf-20e38-pattern-final-affected.log; wf-20e38-pattern-compile.log; wf-20e38-mutants.log; final source SHA256 98d4b2514936f8de88f5f037e0c169f3169e397f0a721f83321d9f367ccc517d |
| 2026-10-11 | Observe: all 12,352 tests passed across 185 files, with 12 existing skips, but canonical run exited 1 because coordinator appended initial_delivery to events.jsonl during execution. No green receipt claim. Thought: qualify a byte-identical isolated copy while the four fresh required delivery lanes independently check changed boundaries; no delivery Council or broad audit. | /private/tmp/wf-20e38-canonical-final.log; repository-change guard names only this wave ledger; final source remains frozen |
| 2026-10-11 | Observe: all four fresh required delivery lanes independently approved with no findings, unchanged nine-path fingerprints, meaningful assertion-failing guard mutants and no unintended skips. Canonical isolated receipt remains pending; no source repair or Council rerun is needed. Code review disclosed unextracted generic turbofish calls as an unsupported-form coverage limit, not a false target. | Current typed delivery approvals; four temporary lane JSON captures; concise synthesis in wave.md |
| 2026-10-11 | Observe: first isolated run passed 184 files but tracked-Python census failed because the coordinator-created no-checkout clone had an empty Git index. Corrected only the temporary index with git read-tree HEAD; canonical focused control passes all 8 tests/zero skips, framework hashes remain identical. Direct script invocation lacked the runner import environment and is not evidence. Thought: rerun the unchanged canonical suite in the validated copy; no source repair or reviewer rerun required. | /private/tmp/wf-20e38-canonical-isolated.log (failed, no receipt); wf-20e38-isolated-parse-control.log (8 pass); wf-20e38-canonical-qualified.log (in progress) |
| 2026-10-11 | Observe: final canonical qualification passed all 12,352 tests/185 files, 12 existing skips, in 986.642s with exit 0 and unchanged isolated tree. Genuine receipt was copied byte-for-byte only after isolated/current/receipt framework hashes matched. All ACs and tasks implemented; four required delivery approvals current, no unresolved finding. New wave remains open for operator-owned closure. | /private/tmp/wf-20e38-canonical-qualified.log; inputs 92477e9a685cbfdde55d993ecdc933318202b093bbd357d66f9c0a5c481dee3c; receipt ran_at 2026-10-11T23:43:56.000809+00:00; full wf_validate_docs and git diff --check pass; owned temporary qualification checkout removed, cited result logs and exact receipt proof retained |
| 2026-10-11 | Close reconciliation: restored the original planning handoff sentence; later status narration belongs in this Progress Log and the current session handoff. The sentence in Session Handoff is the admission-time snapshot, not current state. No requirement, scope or AC changed; current implementation, qualification and delivery approvals are complete. | Original readied plan preserved; current continuation in docs/agents/session-handoff.md |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-11 | Resolve explicit crate-relative free functions through declaration facts and unique crate ownership | Small verifiable expansion preserves conservative guards and avoids runtime/upgrade work | Leaf-name fallback conflates twins/crates; complete Cargo-aware resolution exceeds scope and adds I/O/dependency complexity |

## Risks

| Risk | Mitigation |
| --- | --- |
| Multiple roots/shared or aliased module files conflict | Refuse ambiguous ownership; caller-crate qualification and negative fixtures |
| Topology changes without leaf-name changes | Untouched-caller full/incremental equivalence and context invalidation |
| Extra indexing work or false confidence | Merge-scoped lookups, work-count checks, performance review and unresolved controls |
| Stale loaded MCP implementation | Current-file reads and fresh Python probes; no live graph reliance |

## Session Handoff

See `docs/agents/session-handoff.md`; prior memory wave closed, Rust implementation awaits readiness.
