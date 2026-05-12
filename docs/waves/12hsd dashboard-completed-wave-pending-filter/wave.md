# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-11

wave-id: `12hsd dashboard-completed-wave-pending-filter`
Title: Dashboard: Exclude Completed Waves from Pending Section

## Objective

Fix the pending-wave dashboard defects and the follow-on dashboard operational issues admitted into this wave: dialog detail parsing, files/index tile hierarchy, framework index stale monitoring, and the runtime-cache rebuild loop.

## Changes

Change ID: `12hsc-bug completed-wave-appears-in-pending-section`
Change Status: `complete`

Change ID: `12j27-bug dashboard-dialog-details-parser`
Change Status: `complete`

Change ID: `12j2e-bug framework-index-stale-monitoring`
Change Status: `complete`

Change ID: `12j2j-enh files-tile-lines-changed`
Change Status: `complete`

Change ID: `12j2q-maint remove-dead-files-changed-activity`
Change Status: `complete`

Change ID: `12j2r-bug files-tile-colored-line-deltas`
Change Status: `complete`

Change ID: `12j2v-enh index-tile-combined-totals`
Change Status: `complete`

Change ID: `12j2w-bug normalize-progress-agent-label-typography`
Change Status: `complete`

Change ID: `12j2x-bug index-tile-remove-up-to-date-and-use-files`
Change Status: `complete`

Change ID: `12j3g-bug framework-stale-ignore-pycache`
Change Status: `complete`

Change ID: `12j3w-enh dashboard-index-trigger-logging`
Change Status: `complete`

Change ID: `12j40-enh dashboard-auto-index-default-on`
Change Status: `complete`

Change ID: `12j7e-bug framework-stale-ignore-untracked-directory-entries`
Change Status: `complete`

Change ID: `12j7k-bug framework-stale-use-index-inputs-not-git-dirty`
Change Status: `complete`

Change ID: `12j8w-bug framework-stale-ignore-packaging-artifacts`
Change Status: `complete`

Change ID: `12j9a-enh package-framework-index-incrementally`
Change Status: `complete`

Completed At: 2026-05-11

## Wave Summary

The original three pending-wave fixes are complete, and the wave now also includes the admitted follow-on dashboard work completed afterward: AC/task dialog parsing, files tile simplification to working-tree counts plus line deltas, semantic index tile hierarchy refinements, framework stale/build parity, `__pycache__` / `.pyc` stale-loop suppression, the collapsed-untracked-directory stale-loop fix, the framework-file-meta stale-source correction for packaged repos, the packaging-artifact exclusion that keeps `MANIFEST` / `VERSION` changes from making packaged framework indexes look stale on arrival, and packaging-time framework index updates that now prefer incremental work while still relying on shared indexer fallback when drift requires a full rebuild.

## Journal Watchpoints

- **Watchpoint: other terminal status strings** — only `"completed"` is excluded here; if projects use additional non-standard terminal statuses in the future, `pendingWaves()` may need further extension.
- **Watchpoint: parser compatibility** — dashboard detail dialogs must support both checkbox-style and plain-bullet AC/task sections because existing wave docs in this repository use both formats.
- **Watchpoint: framework index parity** — the dashboard currently computes live stale/build state only for the project layer; keep framework-layer semantics aligned enough that the UI does not imply the framework index is fresh when it may only be old.
- **Watchpoint: files tile signal quality** — prefer durable git-change signals over shallow recency labels; do not duplicate the same file/change summary in multiple UI regions.
- **Watchpoint: cleanup scope** — remove only the dead “files changed today” activity payload/tests; keep working-tree git stats and the all-files dialog untouched.
- **Watchpoint: diff color semantics** — restore the prior green/red diff affordance without reintroducing the removed duplicate header pills.
- **Watchpoint: index tile density** — combine project/framework totals without collapsing freshness/build state back into an overloaded single-line note.
- **Watchpoint: label typography parity** — normalize the visible type treatment without flattening the category-specific color semantics for agent pills.
- **Watchpoint: index tile hierarchy** — keep the primary metric on files only; chunk totals can stay secondary, and “current” should not consume a whole status line.
- **Watchpoint: runtime cache noise** — framework stale checks must ignore Python cache artifacts so idle dashboard imports do not look like fresh source edits.
- **Watchpoint: index trigger observability** — log lines should identify the index layer and trigger reason without masking framework-only rebuilds behind generic project wording.
- **Watchpoint: default auto-index behavior** — missing config should now enable auto-indexing, but explicit `dashboard.auto_index: false` must remain a stable opt-out.
- **Watchpoint: collapsed untracked directories** — stale detection must not stat git-reported directory placeholders whose mtimes can move when excluded framework index outputs are rewritten underneath them.
- **Watchpoint: framework stale source of truth** — the packaged framework docs layer is installed untracked in target repos, so its periodic stale detector must prefer indexed input snapshots over generic git dirty state.
- **Watchpoint: packaging artifacts are not semantic inputs** — `MANIFEST` and `VERSION` may change during packaging, but they must not by themselves make the framework docs index look stale after upgrade.
- **Watchpoint: package-time framework indexing cost** — packaged framework docs search should stay current, but packaging should use incremental updates unless shared indexer drift detection requires a full rebuild.

## Review Evidence

- wave-council-readiness: approved (2026-05-10 — original approved scope covered `pendingWaves()` filter, `.pending-wave-left` column layout, and section-label rule placement)
- wave-council-delivery: approved (2026-05-10 — original three pending-wave fixes delivered, 1087 tests passing, gate closed)
- code-review: approved (2026-05-11 — formal full-scope wave review rerun after the framework stale-detector packaging-artifact fix; no blocking findings remain)
- qa-review: approved (2026-05-11 — targeted dashboard server tests, full framework suite, and docs lint passed)
- review-scope-note: expanded wave scope was re-reviewed on 2026-05-11; the original 2026-05-10 wave-council delivery approval remains historical evidence for the initial three-fix scope
- operator-signoff: approved

## Dependencies

- No external wave dependencies.
