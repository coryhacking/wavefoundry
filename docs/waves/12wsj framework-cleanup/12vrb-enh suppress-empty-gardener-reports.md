# Suppress Empty Gardener Reindex Reports

Change ID: `12vrb-enh suppress-empty-gardener-reports`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-24
Wave: `12wsj framework-cleanup`

## Rationale

`docs_gardener.py` always creates a dated report file (`docs/reports/reindex-YYYY-MM-DD.md`) on the first run of each day, even when no docs were actually stamped. The result is a report that lists only itself in `## Updated Paths` — circular and valueless. These accumulate in git as noise on every package build. The `reindex-registry.md` design spec already states: *"No report file is required for routine reindex passes."* The code just doesn't enforce that intent.

## Requirements

1. When `docs_gardener.py` runs and no docs were stamped (i.e., `updated_paths` is empty before the report block), do not create a report file. Print `docs-gardener: ok (nothing to report)` instead.
2. When at least one non-report path was updated, continue writing the dated report as today (unchanged behavior for meaningful runs).
3. If a dated report file already exists from a prior run on the same day, leave it untouched when the current run has nothing to report (do not delete it).

## Scope

**Problem statement:** The gardener unconditionally creates today's report on first run, producing self-referential reports that add git noise without information content.

**In scope:**

- `docs_gardener.py` — suppress report creation when `updated_paths` is empty
- Existing dated report files in `docs/reports/` — no cleanup required (out of scope)
- `reindex-registry.md` — no change needed (already states the correct intent)

**Out of scope:**

- Deleting or pruning existing accumulated report files
- Changes to the manifest, session-handoff, or any other gardener behavior
- Report format or content changes when reports are written

## Acceptance Criteria

- [x] AC-1: Running `docs_gardener.py` when no docs have changed does not create or modify a dated report file; prints `docs-gardener: ok (nothing to report)`.
- [x] AC-2: Running `docs_gardener.py` when at least one doc is stamped creates the dated report listing the stamped paths (existing behavior preserved).
- [x] AC-3: If a dated report already exists and the current run has nothing to report, the existing file is left untouched.
- [x] AC-4: Framework tests pass.

## Tasks

- [x] In `gardener_run`, wrap the report-write block with a guard: skip file creation when `updated_paths` is empty; print `ok (nothing to report)` message and return without writing.
- [x] Update `render_report` call sites if signature changes are needed.
- [x] Run framework tests to confirm no regressions.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| Script edit | implementer | — | Single-function change in `docs_gardener.py` |
| Test verification | qa-reviewer | Script edit | Framework test suite + manual smoke test |

## Serialization Points

- None — single-file change with no parallel work surface.

## Affected Architecture Docs

N/A — change confined to a single script with no boundary, flow, or verification-topology impact.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | This is the core behavior change: empty gardener runs must stop creating noise files. |
| AC-2 | required | The cleanup must not regress meaningful report generation when docs were actually stamped. |
| AC-3 | required | Existing reports must remain untouched on empty runs to avoid accidental destructive behavior. |
| AC-4 | required | Framework tests are the acceptance proof that the script change did not introduce regressions. |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-05-24 | Change doc created | Observed 7 of 9 report files list only themselves |
| 2026-05-25 | Implemented empty-run suppression in `docs_gardener.py`; added regression coverage for no-op and existing-report cases. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_docs_gardener.py'`; manual smoke `python3 .wavefoundry/framework/scripts/docs_gardener.py --date 2026-05-25` printed `docs-gardener: ok (nothing to report)` |
| 2026-05-25 | Full framework-suite proof completed after the earlier reranker baseline issue was cleared. | `python3 .wavefoundry/framework/scripts/run_tests.py` — 1620 tests, 0 failures |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-24 | Suppress on empty, don't delete existing | Deletion adds complexity; existing files are harmless | Prune old files (out of scope); write single rolling file (loses history) |

## Risks

| Risk | Mitigation |
|---|---|
| Gardener silent-fails on real stamping run | AC-2 explicitly verifies stamped-path behavior is preserved |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
