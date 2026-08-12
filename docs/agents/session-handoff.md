# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-08-12

## Wave `1uwpf receipt-and-citation-contract-followups` — CLOSED 2026-08-10 (uncommitted)

Three changes delivered: `1uu0f` (receipt-authority docs reconciled to shipped code, five drifts), `1uu9y` (symbol-anchor citation rule at review-evidence authoring surfaces), `1uu9z` (twelve unguarded change-doc read sites fixed; unreadable docs now block close instead of being silently skipped; absolute-path leak class closed via `_read_error_detail`). Full ledger: 6/6 lane and council APPROVE across two review rounds, operator signoff recorded, closed via `wf_close_wave`.

`1us4q` (Decision Log churn) was admitted, implemented, falsified by six lanes, WITHDRAWN, and its implementation fully reverted — it is parked in `docs/plans/` carrying the findings. Do not re-attempt without reading its Progress Log.

**Carried-forward findings (need their own changes):** unguarded `wave.md` reads (same crash class, one file over); missing-admitted-doc silently skipped at close; synthetic single-arg `OSError` in the rollback path defeats `strerror`; the review-status reason string says "invalid actor or independence" when the true cause is receipt supersession; `docs/prompts/council-review.prompt.md` has no renderer sync for its citation paragraph; carrier parity unenforced between `REVIEW_POLICY_SURFACE_BLOCKS` and rendered regions; the p95 perf budget in `test_server_context_efficiency` fails under full-suite parallelism at HEAD.

**Nothing committed.** The tree holds this wave plus `1usqm`, `1uugh`, `1ur6o` — all closed, all uncommitted.

## Wave `1usqm citation-durability-and-receipt-integrity` — CLOSED (uncommitted)

Suite **7032 tests OK across 62 files**; docs-lint ok. Nothing committed since `bf085a21`.

### `1urlb-change plans-anchor-by-symbol-not-line-number` — implemented, 7/7 ACs

Symbol-anchor citation rule in seeds 170, 180, 211, propagated to `docs/agents/guru.md` (seed↔doc parity confirmed by SHA-256 on the `## Citation Format` region). Delivery review also caught a fifth carrier nobody counted: the Claude subagent template in `render_agent_surfaces.py` instructed bare `file:line`, contradicting the doc it delegates to. Repaired at source and re-rendered.

### `1upba-bug failed-prepare-appends-receipt-and-lapses-approvals` — implemented, 12/12 ACs

Readiness approvals now refuse against an already-superseded receipt, inside the publication lock, for every receipt-bound readiness key. Degradation splits by typed cause (`PolicyInputError.cause`); only `read` degrades. Close-branch carve-out gates both exits on `never_prepared_under_policy`.

**Known, named discrepancy that ships:** Requirement 9's "faithfully" claim is withdrawn. `wf_mark_ac(state='~')` is a second receipt writer, so one AC deferral on a never-prepared wave re-arms the readiness key. Recoverable (one prepare + one approval); every other population censused unaffected. **Follow-up: reconcile seed `007-review-system-overview.md`'s wording to the implemented rule.**

## Delivery review — COMPLETE, four lanes, all findings folded

All four lanes returned CHANGES REQUESTED; every finding is folded and re-verified. QA ran 22 mutants and found 9 survivors, three against required ACs (AC-3 non-digest fixture, AC-5 coverage, AC-9 ledger-health conjunct in the fail-open direction). All three now have tests and all three mutants were re-run and killed.

## Remaining before close

- **Delivery lane approvals not yet recorded** in the ledger: `code-reviewer`, `qa-reviewer`, `architecture-reviewer`, `docs-contract-reviewer`, plus the required delivery council and operator signoff.
- Readiness approval is recorded, bound to receipt `review-policy-1d603a3387c1ec91ff7c`.

## Follow-ups not in this wave

1. Reconcile seed 007's carve-out wording (above).
2. Review-evidence citation authoring lives in `209-agent-harness-core.prompt.md` and the lane seeds, outside `1urlb`'s declared surfaces; `237-council-review.prompt.md` should be revisited in the same change.
3. `docs/architecture/data-and-control-flow.md` carries three pre-existing drifts. The sole-writer one is now load-bearing for a gate decision, so it is contract-relevant rather than cosmetic.
4. `1us4q` remains parked behind its own census gate, by design.

## Note

`docs/plans/1upqx-...` was deleted (premise disproved at readiness). Wave `1ur6o`'s record retains the full disproof; its two "parked in `docs/plans/`" pointers were removed so nothing dangles.

## Current Session

**Active wave:** *(none)*

### 1.16.0 released 2026-08-11

Tag `v1.16.0`, stamp commit `0324f9ee` (`1.16.0+pig9`), suite 7181 across 62 files, docs-lint ok. Model set v2 published at the permanent `models` tag as `wavefoundry-models-2.zip`. Set 1 stays unpublished (it carries the components the supplier-lineage policy removed), so 1.15.x and earlier have no distributed offline model set.

### Stage-gate waiver — operator-approved, named scope

**Scope:** comment-only corrections in `.wavefoundry/framework/scripts/accel_embedder.py`. No behavioral change, no contract change, no test change.

**Granted by:** operator, in-session, 2026-08-11 ("Also, let's fix the out of date comment").

**Why a waiver rather than a wave:** the edits touch only docstring prose in a framework script, which affects no shipped or verified behavior. Recorded here per the `AGENTS.md` **Stage Gate** exclusion for operator-approved waivers on a named scope.

**What was corrected:** two comments described arctic as having no `CLEAN_ONNX_SOURCES` entry. Wave 1v0r0 registered it at `accel_embedder.py:72`, so both statements inverted the truth.

**Finding surfaced while correcting, NOT acted on:** `_resolve_model_files` returns the clean export first (`:274-276`), so the resident-graph branch at `:277-283` and its `_ensure_fastembed_model_cached` call are now unreachable for every model this set ships. Both arctic and MiniLM L6 are registered in `CLEAN_ONNX_SOURCES`; the branch only runs for an unregistered model. This is dead-for-shipped-models code, not a stale comment, and removing it needs its own change doc and wave. Note it does **not** make the `embedding-fastembed` bundle component redundant: `indexer._get_embedder` reaches fastembed through a different path (`indexer.py:3574-3586`) for small incremental runs and for accel failure on a GPU host.
