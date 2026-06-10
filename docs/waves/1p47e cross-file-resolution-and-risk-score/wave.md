# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-09

wave-id: `1p47e cross-file-resolution-and-risk-score`
Title: Cross File Resolution And Risk Score

## Objective

Fix the call graph's cross-file blast-radius blind spot, then **conditionally** revive `code_risk_score` behind a stage gate. `1p470` replicates the proven TS `import_targets` pattern (wave `1p2tf`) so cross-file `Type.method()` calls produce resolved `calls` edges for the tractable languages (Java/Kotlin/C#/Go + Python static imports), forcing a `GRAPH_BUILDER_VERSION` rebuild — a real `code_impact` improvement independent of any tool. **Then the stage gate:** once `1p470` lands and the graph rebuilds, re-run `code_risk_score`'s AC-8 on real modules; `1p41o` proceeds to implementation **only if** the composite is now non-degenerate (Spearman ρ ≤ ~0.95), otherwise it is re-deferred with the new evidence. Closes when cross-file resolution ships and the gate has decided `1p41o`'s fate (shipped, or re-deferred).

## Changes

Change ID: `1p470-enh cross-file-receiver-resolution-import-tables`
Change Status: `complete`

Change ID: `1p41o-enh code-risk-score-tool`
Change Status: `complete`

Change ID: `1p4dc-doc provision-install-log-format-to-targets`
Change Status: `complete`

Completed At: 2026-06-09

## Wave Summary

Wave `1p47e` (Cross File Resolution And Risk Score) delivered 3 changes: Cross-File Receiver Resolution via Per-Language Import Tables, Add code_risk_score MCP Tool (Composite Symbol Risk — Blast-Radius × Degree, Extensible), and Provision install-log-format.md to Target Projects. Notable adjustments during implementation: Cross-File Receiver Resolution via Per-Language Import Tables: Scoped from a grounded investigation (3-agent workflow over `graph_indexer.py` + wave history). Captured the exact resolution seam, per-language feasibility table, prior-art timeline, consumer-impact matrix, and the `GRAPH_BUILDER_VERSION` obligation. Not yet admitted to a wave.; Cross-File Receiver Resolution via Per-Language Import Tables: **Implemented (operator-directed pivot — see header).** (a) **Lazy-loader return-type inference** in the Python extractor (`graph_indexer.py`): recognizes the sibling-script loader idiom `def _load_X(): return _load_script("mod")` + direct `v = _load_script("mod")`, tracks loader-assigned module vars, and resolves `v.Class.method()` / `v.func()` / inline `_load_X().func()` to the loaded module's symbols. (b) **Language-agnostic import-disambiguation** in the cross-file rewrite pass: an ambiguous `external::Type.method` is filtered to the candidate whose defining module matches the SOURCE FILE's `imports` edge for `Type`. (c) `GRAPH_BUILDER_VERSION` `23`→`24`; graph rebuilt. 6 new tests; full suite **2936 green**.; Add code_risk_score MCP Tool (Composite Symbol Risk — Blast-Radius × Degree, Extensible): **AC-8 stage gate RE-RUN on the rebuilt v24 graph (post-`1p470`) → PASS (pooled), with a documented per-module nuance for AC-9.** Ran the real `GraphQueryIndex.risk_score` over 12 real self-host modules spanning fan-in. **Pooled (833 scored symbols):** CoV(affected_file_count)=**0.981** (≥0.3 precondition PASS); Spearman ρ(risk, fan_in)=**0.796** (≤0.95 INDEPENDENCE PASS, no fallback needed). **Per-module (1p41l-comparable):** degenerate (ρ>0.95) **6/12 (50%)** vs `1p41l` 81%; flat-afc (CoV<0.3) **2/12 (17%)** vs `1p41l` 46% — the cross-file + lazy-loader edges measurably reduced degeneracy. Residual: within tiny single modules with near-uniform blast radius, `risk` still tracks `fan_in` (correct — when afc is uniform the highest-degree symbol *is* the riskiest); the tool's distinct signal is on broad/cross-module scopes where afc varies → folded into AC-9 guidance.

**Changes delivered:**

- **Cross-File Receiver Resolution via Per-Language Import Tables** (`1p470-enh cross-file-receiver-resolution-import-tables`) — 7 ACs completed. Key decisions: --------; **Phase the work: typed langs (Java/Kotlin/C#/Go) + Python static imports first; defer lazy-loader/trait-dispatch/header-split/Sorbet residuals.**
- **Add code_risk_score MCP Tool (Composite Symbol Risk — Blast-Radius × Degree, Extensible)** (`1p41o-enh code-risk-score-tool`) — 9 ACs completed. Key decisions: --------; Named `code_risk_score`, framed as a general composite (not `code_churn_risk`/`code_refactor_risk`)
- **Provision install-log-format.md to Target Projects** (`1p4dc-doc provision-install-log-format-to-targets`) — 5 ACs completed. Key decisions: ------------------------------------------------------------------------------; Mirror the `1p455` pattern: ship as a framework template + seed provisioning.
## Journal Watchpoints

- **STAGE GATE (blocking — the headline of this wave):** `1p41o` (`code_risk_score`) is gated behind `1p470`. Sequence: **(1)** implement `1p470` (cross-file resolution) and rebuild the graph (`GRAPH_BUILDER_VERSION` bump); **(2) GATE — re-run `code_risk_score` AC-8** on ≥2 real modules against the rebuilt graph: confirm `affected_file_count` now varies and compute Spearman ρ(risk, fan_in); **(3) implement `1p41o` ONLY if non-degenerate** (ρ ≤ ~0.95, directly or after the pre-committed rank-normalize fallback). **If it is still a degree proxy, do NOT implement `1p41o` — re-defer it** (`Change Status: deferred` / relocate to `docs/plans/`) with the new evidence. The gate is literally `1p470`'s AC-7 ≡ `1p41o`'s AC-8.
- **Sequencing (blocking):** `1p41o` **depends on** `1p470`. `1p470` must ship and the graph must rebuild before the gate runs; no part of `1p41o` is implemented before the gate passes. Implement order: `1p470` → gate → `1p41o`.
- **Version-bump watchpoint (blocking):** `1p470` MUST bump `GRAPH_BUILDER_VERSION` (`graph_indexer.py:28`, currently `"23"`) in the same change — it alters edge shape, triggering the full synchronous auto-rebuild (`graph_query.py:98-243`). The gate's AC-8 re-run requires that rebuilt graph; running it against a stale graph is invalid.
- **Edit-gate watchpoint:** `1p470` edits `graph_indexer.py` (+ tests + `docs/architecture/graph-index-system.md`) → `framework_edit_allowed`. `1p41o`, *if it proceeds*, edits `graph_query.py` + `server_impl.py` + seed `211-guru.prompt.md` (recipe-depth guidance per its AC-9) → `framework_edit_allowed` + `seed_edit_allowed`.
- **History pointer:** `1p41o` was gated out (AC-8 NO-GO) and deferred in the now-closed `1p41l` on 2026-06-08; it was relocated here to be revisited and set back to `planned` (gated). Its change doc carries the original gate-out evidence (degree proxy on 81% of modules; `from_root` → 0 affected files).
- **Readiness-review fix-during-impl follow-ups (prepare council, 2026-06-09):** during implementation also (a) pin concrete consumer-safety thresholds in `1p470` AC-4 (token cap, modules to spot-check, decider/remediation); (b) correct the stale `docs/architecture/graph-index-system.md:8` v17 citation while editing for AC-6 + add the no-double-resolution spot-check; (c) sharpen the AC-7 ≡ AC-8 wording (1p470 AC-7 is the *measurement*, 1p41o AC-8 the *decision*); (d) add the explicit `1p470` dependency edge to `1p41o`'s Agent Execution Graph. The gate's pass-condition, phase-scope, and auditable-ρ-evidence (must-fixes #1/#2/#5) were applied in-session to `1p470` AC-3/AC-7 + `1p41o` AC-8.

## Review Evidence

- wave-council-readiness: approved 2026-06-09 — READY (PASS WITH IN-SESSION FIXES; full depth; seats: architecture CONCERN / reality-check BLOCK / qa READY / red-team CONCERN / docs-contract CONCERN; moderator: READY-WITH-FIXES, 4 must-fix all applied in-session — (1) **gate pass-condition** now quantified: non-degeneracy precondition (`affected_file_count` CoV ≥ 0.3 across ≥10 fan-in-spanning modules) → Spearman ρ ≤ 0.95 → pre-committed rank-normalize fallback, with mandatory recorded ρ/CoV/module-list evidence, in `1p470` AC-7 + `1p41o` AC-8; (2) **gate phase-scope**: measure after the FULL `1p470` (Phase 1 typed-lang + Phase 2 Python), since the self-host sample is Python-heavy; (3) `1p470` **AC-3 target pinned** `"23"`→`"24"` + rebuild-success assertion; (4) `1p470` **AC Priority table populated** (all 7 ACs). Strongest challenge (red-team): the gate vests ship/defer in the team that built its dependency — mitigated by mechanizing the threshold so a borderline ρ (0.94 vs 0.96) is decided by recorded numbers, not interpretation. Stage-gate decidability: NOW DECIDABLE. `1p4dc`: READY, no blockers. Remaining 4 findings are fix-during-impl (recorded in Journal Watchpoints). **Operator note: the CoV ≥ 0.3 / ≥10-module / ρ ≤ 0.95 thresholds were prepare-authored — confirm or adjust at `wave_implement` before implementation.**)
- wave-council-delivery: READY-WITH-NOTES 2026-06-09 — shipped code is real, safe, and never over-resolves (verified independently by 4 seats: `from_root` 0→12 in-edges on the live v24 graph, suite 2946 green, risk_score faithful to spec, docs/seed/guru in sync). 3 doc-only over-claim notes were APPLIED at close: **N1** AC-8 per-module ρ corrected for Spearman tie-handling (graph_query 0.71→0.91) + machine-local-graph caveat — the pooled-ρ gate criterion still PASSES and reproduces (proper pooled ρ=0.80 ≤ 0.95, per-module degeneracy 39% with default filter, down from 81%); **N2** `1p470` typed-lang coverage scoped to verified **Python+Java** (C#/Go/Rust import-head fix tracked in `1p4ef`); **N3** `wave.md` gate-enabler narrative reconciled (gate passed pre-`1p470`). No blocking finding (seats: qa READY / red-team CONCERN / architecture READY / docs-contract CONCERN). The leaked-`qualified` bug (architecture seat) + Java same-package miss are correctly deferred to `1p4ef`.
- operator-signoff: approved — operator confirmed closure 2026-06-09 ("Yes"). AC-8 gate GO ("pass") recorded; `code_risk_score` + cross-file resolution validated by the 1.6.0+p4ea test pack across 3 teams (Java/Swift/JS-TS); the one observed gap (Java same-package ambiguous receiver) + `code_impact` polish items are scoped to the follow-on (`docs/plans/1p4ef-bug graph-qualified-index-leaked-loop-var.md`).

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-09: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the stage-gate pass-condition was underspecified and vests ship/defer in the team that built its dependency — borderline ρ invited motivated reasoning; FIXED in-session by mechanizing it (non-degeneracy `affected_file_count` CoV ≥ 0.3 across ≥10 fan-in-spanning modules → Spearman ρ ≤ 0.95 → pre-committed rank-normalize fallback, with mandatory recorded ρ/CoV/module evidence) in `1p470` AC-7 + `1p41o` AC-8, plus gate phase-scope (full `1p470` Phase 1+2), `1p470` AC-3 target pin `23`→`24`, and the `1p470` AC Priority table — 4 must-fix applied, 0 remaining; strongest-alternative: none material — `1p4dc` reference-doc provisioning in a graph-tools wave is a placement preference (not a readiness defect) and mirrors the proven `1p455` pattern; 4 fix-during-impl follow-ups recorded in Journal Watchpoints; operator to confirm the prepare-authored gate thresholds at `wave_implement`)

## Dependencies

- No external wave dependencies.
