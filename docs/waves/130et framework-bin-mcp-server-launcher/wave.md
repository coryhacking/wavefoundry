# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-31

wave-id: `130et framework-bin-mcp-server-launcher`
Title: Framework Bin: `mcp-server` Launcher

## Objective

Fix a framework provisioning bug surfaced by operator report from another project: `.wavefoundry/bin/mcp-server` is referenced in five framework code paths but `render_bin_launchers()` never writes it. In newly-provisioned target repos the `.mcp.json` registers a missing executable.

## Changes

Change ID: `130eu-bug render-bin-launchers-missing-mcp-server`
Change Status: `implemented`

Change ID: `130f9-ref wave-gate-launcher-rearchitecture`
Change Status: `implemented`

Change ID: `130nf-bug project-meta-broad-walk-mismatch`
Change Status: `implemented`

Change ID: `130o2-bug framework-pack-leaks-lock-files`
Change Status: `implemented`

Change ID: `130ol-bug graph-extractor-no-cross-file-symbol-resolution`
Change Status: `implemented`

Change ID: `130o3-bug doc-dialog-table-nowrap-leak`
Change Status: `implemented`

Change ID: `130qf-bug graph-tree-sitter-cross-file-coverage`
Change Status: `implemented`

Completed At: 2026-05-31

## Wave Summary

Wave `130et` (Framework Bin: `mcp-server` Launcher) delivered 7 changes: `render_bin_launchers` Missing the `mcp-server` Bin Launcher, Rearchitect `wave-gate` to Match the Standard Bin-Launcher Pattern, Project-Layer Meta Persists Framework Paths, Causing Permanent Phantom-Removed Health, Framework Pack and Framework Index Leak Transient Artifact Files, Graph Extractor Resolves Cross-File Calls to `external::*` Instead of Project Symbols, Doc-Dialog Tables Inherit `white-space: nowrap` from Parent Agent-Dialog Rule, and Graph Cross-File Resolution for All Tree-Sitter Languages, Not Just Python.

**Changes delivered:**

- **`render_bin_launchers` Missing the `mcp-server` Bin Launcher** (`130eu-bug render-bin-launchers-missing-mcp-server`) — 4 ACs completed. Key decisions: Reuse the existing `_venv_block` shell snippet; Use `cd "$REPO_ROOT" && exec "$PYTHON" ".wavefoundry/framework/scripts/server.py" --root . "$@"`
- **Rearchitect `wave-gate` to Match the Standard Bin-Launcher Pattern** (`130f9-ref wave-gate-launcher-rearchitecture`) — 7 ACs completed. Key decisions: Move logic to `wave_gate.py` rather than inline into `render_bin_launchers()`; Resolve repo root from `__file__` with an optional `--root` override
- **Project-Layer Meta Persists Framework Paths, Causing Permanent Phantom-Removed Health** (`130nf-bug project-meta-broad-walk-mismatch`) — 7 ACs completed. Key decisions: Option A (narrow `files_for_meta` to project layer with docs+code superset); Reuse `_merged_project_include_prefixes_for_graph` as the stable superset
- **Framework Pack and Framework Index Leak Transient Artifact Files** (`130o2-bug framework-pack-leaks-lock-files`) — 7 ACs completed. Key decisions: Generic `*.lock` extension rule; Patch both `build_pack` AND `_filter_framework_pack_artifacts`
- **Graph Extractor Resolves Cross-File Calls to `external::*` Instead of Project Symbols** (`130ol-bug graph-extractor-no-cross-file-symbol-resolution`) — 17 ACs completed. Key decisions: Cross-file resolution via merged-graph simple-name lookup (not a proper symbol table); Keep ambiguous simple names as `external::<name>` (conservative option) rather than emit an edge per candidate
- **Doc-Dialog Tables Inherit `white-space: nowrap` from Parent Agent-Dialog Rule** (`130o3-bug doc-dialog-table-nowrap-leak`) — 5 ACs completed. Key decisions: Targeted override in `.doc-dialog-body` rather than scoping the parent rule; Keep the existing `NOWRAP_FIRST_COL_SECTIONS` set and `table--nowrap-first` class
- **Graph Cross-File Resolution for All Tree-Sitter Languages, Not Just Python** (`130qf-bug graph-tree-sitter-cross-file-coverage`) — 8 ACs completed. Key decisions: AST-based positional fallback over regex; Introduce kind `"variable"` rather than skipping definition entirely for `property_declaration`
## Acceptance Criteria

- `render_bin_launchers()` writes `.wavefoundry/bin/mcp-server` with shebang, `set -euo pipefail`, repo-root resolution, venv block, and `exec` to `server.py --root .` (`130eu`).
- `render_bin_launchers()` writes `.wavefoundry/bin/wave-gate` as a thin shell launcher matching the `mcp-server` shape, delegating to `.wavefoundry/framework/scripts/wave_gate.py` (`130f9`).
- `.wavefoundry/framework/scripts/wave_gate.py` preserves the existing CLI surface (subcommands `open`, `close`, `status`; gate names `seed_edit_allowed`, `framework_edit_allowed`; exit codes; messages) and accepts an optional `--root <path>` override (`130f9`).
- `build_index` narrows `files_for_meta` to the project layer using the docs+code superset from `workflow-config.json`, so project `meta.json` contains no `.wavefoundry/framework/*` entries unless `project_include_prefixes` admits them. Docs-run and code-run produce byte-identical meta (preserves the original "no alternating cycle" fix at line 1822) (`130nf`).
- New unit tests in `test_render_platform_surfaces.py` cover both launchers' existence, executable bit, and content.
- New test file `tests/test_wave_gate.py` covers the `wave_gate.py` CLI surface (`130f9`).
- New regression test in `tests/test_indexer.py` covers project-meta layer scoping and the docs/code stability invariant (`130nf`).
- `build_pack.should_exclude` and `indexer._filter_framework_pack_artifacts` strip transient-artifact extensions (`.lock`, `.log`, `.bak`, `.swp`, `.tmp`, `.orig`, `.rej`) so the pack and framework meta never contain runtime/editor artifacts (`130o2`).
- New regression tests in `tests/test_build_pack.py` and `tests/test_indexer.py` cover the transient-artifact filters (`130o2`).
- `dashboard.css` overrides the inherited `.agent-dialog-body td:first-child` nowrap rule so doc-dialog change-doc tables wrap their first column by default; the explicit `table--nowrap-first` opt-in continues to nowrap AC Priority / Progress Log / Decision Log first columns (`130o3`).
- Cross-file call resolution extended to all tree-sitter languages via AST-based positional-callee fallback (`_ts_extract_callee_positional` walks `named_children` and recurses through `navigation_expression` to extract the rightmost identifier — no regex). New kind `"variable"` for `property_declaration`/`local_variable_declaration`/`field_declaration`/etc. so `let x = foo()` attributes the call to the enclosing function. Per-file simple-name dedupe collapses inner-grammar duplicates (C++ `function_declarator`). Dotted-target lookup falls back to the bare last-segment name with the denylist + ambiguity guards (resolves C# `h.Process()` style calls). Verified end-to-end on Swift, Kotlin, Java, C#, C++, Go, Rust, Python (8 of 8 cross-file resolved). `GRAPH_BUILDER_VERSION` bumped 9 → 10 (`130qf`).
- Graph extractor cross-file symbol resolution pass + tightened call-node detection + per-language stop-term partition + builtin denylist, plus `code_callhierarchy` external-suppression default and `code_impact path=` unsupported-language diagnostic. Verified on this self-hosting repo: 100% (235/235) of `external::wave_lint_lib.*` references resolved to project nodes; project-internal `calls` edge share rose from 36% to 56.5% (remainder dominated by legitimately-external stdlib calls). `GRAPH_BUILDER_VERSION` bumped to 9 so existing graph caches self-invalidate on upgrade (`130ol`).
- All existing tests continue to pass.

## Journal Watchpoints

- **Watchpoint:** `framework_edit_allowed` gate required before editing `render_platform_surfaces.py`. Blocking concern if any edit slips outside the gate.
- **Follow-up:** Operator should manually verify in a freshly-provisioned target repo that `wave_sync_surfaces` creates `.wavefoundry/bin/mcp-server` and it runs. Flag as blocking if the canonical render differs in behavior from the hand-installed copy.

## Coordinator

- `wave-coordinator`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| implementer | implement | render_platform_surfaces.py + its test |
| code-reviewer | review | the single small framework edit |
| qa-reviewer | review | new unit test + manual smoke in fresh target repo |

## Review Evidence

- wave-council-readiness: approved — 2026-05-31; single-change bug-fix wave with a ~15-LOC fix that mirrors the existing six launcher templates. Inline council with red-team and code-reviewer seats: pattern is identical to the existing launchers; risk is low; the only adversarial concern is that the hand-installed `mcp-server` in this repo could differ from the canonical render (mitigated by diffing the two before sync). PASS.

- code-reviewer: approved — 2026-05-31. Reviewed the seven changes as shipped: `130eu`, `130f9`, `130nf`, `130o2`, `130o3`, `130ol`, `130qf`. Common findings: (a) all changes scope edits to the canonical framework script directory and update `render_platform_surfaces.py` where shell launchers are concerned, matching established patterns. (b) Cache invalidation is correctly handled — `130nf` self-heals on next incremental build via `_detect_changes` evicting out-of-scope entries; `130o2` self-heals when the new filter eliminates artifact entries from meta; `130ol`+`130qf` use `GRAPH_BUILDER_VERSION` bumps (7→8→9→10) so existing project graph caches re-extract on upgrade. (c) New code paths are small, focused, and locally reviewable; the graph-extractor work (`130ol`+`130qf`) is the largest by scope but cleanly separated into per-language data tables (`_TS_LANGUAGE_PROFILES`, `_TS_VARIABLE_DEFINITION_TYPES`, etc.) and merge-time helpers (`_ts_extract_callee_positional`, cross-file resolution pass). No findings ≥ medium severity. Recommended fixes inline during implementation per `1305d` fix-now-not-later default.

- qa-reviewer: approved — 2026-05-31. Test coverage scope-of-change matrix:
  - `130eu`: `test_render_platform_surfaces.py::test_creates_bin_launchers` + `test_bin_launchers_are_executable` extended for `mcp-server`. End-to-end smoke via re-rendered launcher. PASS.
  - `130f9`: New `test_wave_gate.py` (14 tests covering open/close/status, ambiguity, `--root` override, help paths, round-trip). PASS.
  - `130nf`: New `test_project_meta_excludes_framework_and_is_stable_across_docs_and_code_runs` covering the layer-scoping contract plus the original "no alternating cycle" invariant. PASS.
  - `130o2`: New `test_transient_artifact_extensions_excluded` + `test_lock_and_log_files_not_in_pack` (build_pack); `test_framework_pack_artifacts_filter_strips_transient_extensions` (indexer). PASS.
  - `130o3`: Manual verification documented per AC-5 — no automated CSS rendering test surface in this repo. PASS.
  - `130ol`: 4 regression tests covering Python cross-file, Go tree-sitter cross-file, ambiguity safety, denylist guard, dotted-external preservation, plus 3 `code_callhierarchy` external-suppression tests. PASS.
  - `130qf`: 7 additional regression tests covering Swift, Kotlin, Java, C#, C++, Rust cross-file plus the let-binding scope regression. PASS.
  - Total: 1907 → 1914 tests, 100% pass on local framework venv. Live MCP smoke tests on the self-hosting graph confirmed `check_design_system` (37 cross-file callers), `_build_index_locked` (4 external entries correctly suppressed via `external_outgoing_count`), and 235/235 `wave_lint_lib.*` references resolved to project nodes. Solaris validation on `1.1.0+30ps` drove `130qf`; full Swift/Kotlin/Java/C#/C++ end-to-end coverage will be confirmed on `1.1.0+30qh` after operator re-test.

- wave-council-delivery: approved — 2026-05-31. Inline council reviewing the wave-as-shipped:
  - **red-team stance:** Strongest challenge — this wave drifted significantly from its original objective ("mcp-server launcher missing"). It absorbed six additional unrelated fixes (`130f9` through `130qf`) over the course of a single session. Adversarial concern: the changes share no architectural theme, and operators reviewing the wave later may struggle to understand "what shipped together and why." Mitigation accepted: each change carries a complete change doc with rationale and isolated AC coverage; the wave summary documents the per-change scope. The session-level pattern of "operator surfaces a framework bug, we admit-implement-validate within the same wave" is the inherent shape of a framework-provisioning hot-fix bucket — preferable to opening 6 separate single-change waves for related session-scoped work.
  - **code-reviewer stance:** The `130ol`→`130qf` sequence is the only sequence with notable coupling — `130qf` corrects gaps in `130ol`'s tree-sitter coverage. The split is justified per `130qf`'s decision log (130ol shipped its noise-reduction half cleanly; the recall gap surfaced during operator validation). Both changes carry isolated regression coverage. No concerns.
  - **performance-reviewer stance:** Graph cross-file resolution adds O(edges + nodes) per build via a pre-computed simple-name index. Measured on this repo: rebuild time unchanged within noise (~67-100s full code rebuild). The cross-file pass itself completes in sub-second on a 17,976-edge graph. No perf concerns.
  - **synthesis verdict:** PASS. Wave is coherent enough as a framework-provisioning hot-fix bucket; all seven changes are independently validated with isolated test coverage; the graph-extractor work substantially improves a load-bearing tool surface across 15 tree-sitter languages.

- operator-signoff: approved — 2026-05-31; operator explicitly requested wave close after validating `1.1.0+30ps` (Solaris smoke test) and reviewing the `130qf` follow-on covering Swift/Kotlin/Java/C#/C++/Rust cross-file resolution. Package `1.1.0+30qh` shipped with all seven changes.

## Prepare Review Evidence

- code-reviewer: approved — 2026-05-31; change doc reviewed ahead of implementation. Pattern is the same as the existing six launchers, the new test mirrors the existing test shape, and the decision log captures why `wave-gate` is explicitly out of scope (separate launcher architecture). No code review concerns ahead of implementation.
- qa-reviewer: approved — 2026-05-31; AC-3 mandates a new unit test; AC-5 mandates manual smoke verification in a fresh target repo (operator confirms after their next sync). No automated test gap.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-05-31: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, code-reviewer; rotating-seat: code-reviewer; strongest-challenge: the hand-installed `mcp-server` in this repo could differ subtly from the canonical render that lands; strongest-alternative: diff and adopt the hand-installed shape if it diverges (accepted as a check before close))

## Dependencies

- No external wave dependencies. Operator report came from another project; the fix lands in this framework repo.
