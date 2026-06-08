# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-06-08

wave-id: `1p47e cross-file-resolution-and-risk-score`
Title: Cross File Resolution And Risk Score

## Objective

Fix the call graph's cross-file blast-radius blind spot, then **conditionally** revive `code_risk_score` behind a stage gate. `1p470` replicates the proven TS `import_targets` pattern (wave `1p2tf`) so cross-file `Type.method()` calls produce resolved `calls` edges for the tractable languages (Java/Kotlin/C#/Go + Python static imports), forcing a `GRAPH_BUILDER_VERSION` rebuild — a real `code_impact` improvement independent of any tool. **Then the stage gate:** once `1p470` lands and the graph rebuilds, re-run `code_risk_score`'s AC-8 on real modules; `1p41o` proceeds to implementation **only if** the composite is now non-degenerate (Spearman ρ ≤ ~0.95), otherwise it is re-deferred with the new evidence. Closes when cross-file resolution ships and the gate has decided `1p41o`'s fate (shipped, or re-deferred).

## Changes

Change ID: `1p470-enh cross-file-receiver-resolution-import-tables`
Change Status: `planned`

Change ID: `1p41o-enh code-risk-score-tool`
Change Status: `planned`

## Wave Summary

Two coupled changes with a hard gate between them. **`1p470`** (cross-file receiver resolution via per-language import tables) is the enabler — it makes cross-file `Class.method()` calls resolvable at index time, fixing a real `code_impact`/`graph_impact` under-reporting limitation. **`1p41o`** (`code_risk_score`) was gated out at AC-8 in `1p41l` (a `fan_in` degree proxy on 81% of modules, because the blast-radius term was near-constant without cross-file edges); it is relocated here to be **re-attempted only if `1p470` makes the blast-radius signal vary**. The gate — `1p470`'s AC-7, which *is* `1p41o`'s AC-8 re-run — is the go/no-go between the two. `1p41o`'s full gate-out evidence (from `1p41l`, 2026-06-08) travels with its change doc.

## Journal Watchpoints

- **STAGE GATE (blocking — the headline of this wave):** `1p41o` (`code_risk_score`) is gated behind `1p470`. Sequence: **(1)** implement `1p470` (cross-file resolution) and rebuild the graph (`GRAPH_BUILDER_VERSION` bump); **(2) GATE — re-run `code_risk_score` AC-8** on ≥2 real modules against the rebuilt graph: confirm `affected_file_count` now varies and compute Spearman ρ(risk, fan_in); **(3) implement `1p41o` ONLY if non-degenerate** (ρ ≤ ~0.95, directly or after the pre-committed rank-normalize fallback). **If it is still a degree proxy, do NOT implement `1p41o` — re-defer it** (`Change Status: deferred` / relocate to `docs/plans/`) with the new evidence. The gate is literally `1p470`'s AC-7 ≡ `1p41o`'s AC-8.
- **Sequencing (blocking):** `1p41o` **depends on** `1p470`. `1p470` must ship and the graph must rebuild before the gate runs; no part of `1p41o` is implemented before the gate passes. Implement order: `1p470` → gate → `1p41o`.
- **Version-bump watchpoint (blocking):** `1p470` MUST bump `GRAPH_BUILDER_VERSION` (`graph_indexer.py:28`, currently `"23"`) in the same change — it alters edge shape, triggering the full synchronous auto-rebuild (`graph_query.py:98-243`). The gate's AC-8 re-run requires that rebuilt graph; running it against a stale graph is invalid.
- **Edit-gate watchpoint:** `1p470` edits `graph_indexer.py` (+ tests + `docs/architecture/graph-index-system.md`) → `framework_edit_allowed`. `1p41o`, *if it proceeds*, edits `graph_query.py` + `server_impl.py` + seed `211-guru.prompt.md` (recipe-depth guidance per its AC-9) → `framework_edit_allowed` + `seed_edit_allowed`.
- **History pointer:** `1p41o` was gated out (AC-8 NO-GO) and deferred in the now-closed `1p41l` on 2026-06-08; it was relocated here to be revisited and set back to `planned` (gated). Its change doc carries the original gate-out evidence (degree proxy on 81% of modules; `from_root` → 0 affected files).

## Review Evidence

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.
