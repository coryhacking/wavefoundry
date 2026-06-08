# Session Handoff

Owner: wave-coordinator
Status: active
Last verified: 2026-06-08

## Last Closed Wave

**Wave:** `1p41l graph-tools-field-feedback-round-5` — closed 2026-06-08 (uncommitted). Shipped the doc-gap fixes (`1p41m`: seed-211 betweenness anti-pattern note + `mcp-tool-surface` section list; `1p41n`: `guru.md` regenerated from seed-211, body byte-identical) + `1p466` (dashboard untracked-dir `-z` accounting fix — `_iter_porcelain_z`, `--untracked-files=all -z` + `ls-files -z`, incl. an adversarial-verification-caught `.strip()`-corrupts-`-z` bug fixed via `run_raw`). **All net-new graph tools deferred/gated:** `1p41o` (`code_risk_score`) gated out at AC-8 (degree proxy on 81% of modules — call graph lacks cross-file `Class.method` edges; query-layer method reverted), `1p41q` (narrate) deferred, `1p41p` (coverage-gap) dropped; `1p41o`/`1p41q` retained in-wave as `Change Status: deferred`. 2792 tests green; delivery-council PASS.

Prior closes: `1p45n` (readiness/activation decoupling — `wave_prepare(mode='ready')` + single-OPEN guard moved to activation transitions; **live after MCP reload**), `1p458` (dashboard timeline id-wrap + deferred-as-outstanding-while-open).

## Open Waves

- **`1p47e cross-file-resolution-and-risk-score`** — **`planned`** (created this session; `next_action: prepare_wave`). Two coupled changes with a **stage gate** between them: `1p470` (cross-file receiver resolution via per-language import tables — replicates the TS `import_targets` pattern; Java/Kotlin/C#/Go + Python static imports; mandatory `GRAPH_BUILDER_VERSION` bump) → **GATE: re-run `code_risk_score` AC-8 on the rebuilt graph** → `1p41o` (`code_risk_score`, relocated from closed `1p41l`, re-set to `planned`) implemented **only if** non-degenerate, else re-deferred. Next: `wave_prepare` when prioritized.
- **`1p44n framework-1p6-hardening`** — `paused` (21 changes; secrets-scanner + upgrade hardening; uncommitted WIP). Includes `1p45b-bug lifecycle-id-dedup-across-plans-waves-adrs`, now carrying the full MCP-first-minting scope (runtime CLI stderr reminder + doc-level nudge steering callers to `wave_new_*` / `wave_create_wave`). Post-prepare admission watchpoint: `1p45b` + `1p457` need a targeted readiness pass before implementing. Resume via `wave_prepare(mode='create')`. **(`1p41l` closed; no wave is currently OPEN. Single-OPEN: `1p44n` and `1p47e` may both be planned/prepared, but only one activated at a time.)**

## Open Questions / Deferred Decisions

- **Uncommitted:** `1p458`, `1p45n`, and `1p41l` are all **closed but uncommitted** (operator has not requested a commit this session).
- **Dashboard file-count discrepancy — RESOLVED** as `1p466-bug` in wave `1p41l` (this session): `dashboard_lib.py` now enumerates untracked content individually via `git status --untracked-files=all -z` + `ls-files -z` through a NUL-aware `_iter_porcelain_z`, so the tile count, dialog list, and added-line total reconcile (incl. non-ASCII/spaced names + tracked renames). Adversarial verification additionally caught + fixed a `.strip()`-corrupts-`-z` bug (`run_raw`).
- **Graph-extraction follow-up (highest-leverage, surfaced by `1p41o` gate-out):** the call graph systematically lacks cross-file `Class.method()` `calls` edges (87% of `calls` edges are intra-file `EXTRACTED`), so `code_impact`/`graph_impact` under-report cross-file blast radius (`from_root` → 0 affected files). This blocks `code_risk_score` (retained in closed `1p41l` as `deferred`, full evidence in its change doc) and degrades method-level impact analysis. Logged in the MCP code-tool quality memory. **Now a planned WAVE — `1p47e`** (created this session): `1p470` (the cross-file resolution enhancement — replicate the TS `import_targets` pattern for Java/Kotlin/C#/Go + Python static imports; defer lazy-loader/trait/header/Sorbet residuals; mandatory `GRAPH_BUILDER_VERSION` bump) + `1p41o` (`code_risk_score`, relocated from `1p41l`) with a **stage gate** between — `1p41o` implements only if its AC-8 re-runs non-degenerate against the post-`1p470` graph, else re-deferred. Ready to `wave_prepare`.
- `1p45n` chose Option C (no new wave status); Option B (a durable, dashboard-visible `ready` status) is reserved if "readied" should become first-class.

## Current Session

**Active wave:** *(none)* — `1p41l` closed; no wave is OPEN. Two non-closed waves: `1p44n` (`paused`) and the new `1p47e` (`planned`: `1p470` + gated `1p41o`). Either can be Prepared; single-OPEN means only one is activated at a time. No commits made this session (all closed waves uncommitted, per policy).
