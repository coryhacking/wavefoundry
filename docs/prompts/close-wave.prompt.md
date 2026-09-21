# Close Wave

Owner: Engineering
Status: active
Last verified: 2026-09-21

Shortcut: **`Close wave`**

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose models and reasoning effort for reconciliation and unresolved judgments by task fit. Efficient routine checks do not waive review evidence or explicit operator closure authority. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose

Finalize and archive the wave. Closure requires full reconciliation — not just a status flip.

## Closure Requirements (all must be met)

All closure-time code and docs investigation follows the run contract's Retrieval Rules (`.wavefoundry/framework/seeds/020-run-contract.prompt.md`): MCP retrieval tools first, for every lane and briefed subagent.

1. All changes marked `complete` or `deferred` with explicit rationale
2. All required review lanes from readiness reconciled in `## Review checkpoints` (or deferred with rationale)
3. When review is enabled, `wave-council-readiness` is present and `wave-council-delivery` is present only when selected by the current Prepare receipt in `## Review Evidence`
4. **Docs-contract review:** recorded as performed with findings, or `Docs-contract review: not applicable` with rationale — required whenever any `docs/specs/*.md` changed during the wave
5. Chronology reconciled: `Status: completed`, `Completed at:` date, all change statuses finalized
6. Memory capture: important implementation/review lessons recorded as typed memory candidates and validated at the close checkpoint (absence of new candidates is acceptable if nothing warranted one)
7. Durable memory promoted to `docs/references/project-context-memory.md` (and other canonical docs when applicable)
8. **Retrospective step completed:** ask "what was non-obvious in this wave that a future session should know?" — surface memory candidates for architectural decisions (why an approach was chosen), validated approaches that should carry forward (positive confirmations, not only corrections), and workflow discoveries; promote findings to auto-memory or `docs/references/project-context-memory.md`
9. `docs/agents/session-handoff.md` updated to idle format: last-closed wave ID and one-line summary of what shipped, plus an **Open questions / Deferred decisions** section for any intent not captured in a change doc
10. **Hard checkbox gate** (wave 1p31b / 1p32k): every AC and every task across the wave's admitted changes is marked either `[x]` (completed) or `[~]` (intentionally deferred). Silent `[ ]` items block close — `wf_close_wave` returns a `silent_unchecked_items_at_close` diagnostic listing each one. ACs at `not-this-scope` priority are exempt (the priority encodes the exclusion). See `170-plan-feature.prompt.md` "AC and task checkbox states — the `[~]` marker" for the canonical convention.

**Closure is blocked until all ten items are explicitly recorded in the wave record.**

**Automatic gate — framework test receipt** (wave `1wur7`, framework SOURCE repositories only, nothing to record by hand): `wf_close_wave` verifies the existing `.wavefoundry/framework/test-cache.json` receipt — `result == "ok"` with an `inputs_hash` matching the current framework tree — and returns a blocking `framework_test_receipt_not_proven` diagnostic when it is missing, red, stale, or unreadable. Read the `framework_test_receipt` field on the response; do not invent a checklist line for it. The gate runs no suite and spawns no subprocess; record a fresh receipt with `python3 .wavefoundry/framework/scripts/run_tests.py`, and run it LAST, because any edit under `.wavefoundry/framework/` (a seed edit made during closure included) invalidates the receipt. Two scope facts belong together. The receipt's `inputs_hash` covers `.wavefoundry/framework/` only, so only its STALENESS is framework-scoped. But `run_tests.py` writes a receipt only when the WHOLE suite is green, so a failure triggered by content under `docs/` prevents a NEW receipt from being written; when the framework tree also changed the standing receipt is stale and close is blocked, while in a documentation-only wave a current green receipt persists and close is not blocked despite a red suite. The gate is therefore not a whole-repository *guarantee* (a green receipt attests the framework code, not the tree), and it is not a whole-repository *exemption* either. Where the runner is absent — any repository consuming the packaged framework, since the distribution excludes it — the check is a documented no-op that neither blocks nor claims proof, and this item does not apply.

**Close-handoff surfacing of `[~]` items:** the close summary in `## Wave Summary` must list every `[~]` AC across the wave's admitted changes, grouped by change, with the inline status note. Future-readers see them as one discoverable list of intentional deferrals rather than scattered across individual change docs.

## Wave-folder cleanup

Before final docs validation and the close mutation, tidy only artifacts established to belong to this wave. Dates and filenames are discovery hints, not proof of ownership.

- Keep `wave.md`, admitted change docs and authoritative `events.jsonl` in place. Preserve unique review evidence, reproducible probes and historical fingerprints needed to substantiate claims. Never rewrite ledger history for cosmetic cleanup.
- Remove only verified disposable scratch output or redundant copies with no unique evidence and no live references. If ownership, uniqueness or reference use is uncertain, retain the artifact and note why.
- Group movable supporting files under `evidence/` when useful; no fixed layout is required. Keep ledger-cited paths stable. Update mutable links and reproduction commands after any move, and verify they resolve and remain usable. Leave other waves and unrelated files untouched.
- Consolidate repeated status notes into the final outcome and an evidence index in the existing wave summary or delivery report; do not erase historical review conclusions. Record the cleanup disposition and retained exceptions there, then run the existing docs gate. No separate cleanup report or new validator is required.

## What Goes in Wave Summary

`## Wave Summary` is populated at closure. Include:
- What was delivered
- What was deferred (with rationale)
- Key decisions made during the wave
- Lessons promoted to memory records or canonical docs

## Wavefoundry-Specific Closure Checks

- Do not finalize with an unreconciled `tree_moved_under_review` finding: a lane that saw the tree change under it holds evidence for an earlier tree (seed 190).
- Advisory docs-lint findings (`WARNING:` lines from sensors registered `advisory` in `wave_lint_lib/constants.py`, surfaced by `wf_close_wave` as `docs_lint_warning` diagnostics with `advisory: true`) are review notes at close, never a closure blocker; a flip to blocking is a recorded change decided at the release checklist (seed 190).
- If framework scripts changed: confirm `python3 .wavefoundry/framework/scripts/run_tests.py` passes
- If `docs/prompts/` or manifest changed: confirm docs gate passes (**`wf_validate_docs`** over MCP, or **`wf docs-lint`** if MCP is unavailable)
- If seed prompts changed: confirm guard-overrides reset to `false`
- If Wave Council is enabled: confirm `wave-council-readiness` is current and confirm `wave-council-delivery` only when the current Prepare receipt selected it (typed approval events in the wave's `events.jsonl` on declared waves, projected into `## Review Evidence`; prose lines count only on legacy waves)

## Agent Memory Validation Checkpoint

Before closure, run `memory_propose(wave_id, mode='create')`, then validate
every evidence-derived candidate with `memory_validate`:

- Follow the linked evidence and inspect the current target.
- State what changes the next action.
- Check durability, canonical overlap, target accuracy, existing
  duplicates/contradictions, and confidence.
- Choose **promote**, **retain**, **reject**, or **rewrite**.

This is a bounded focused curation pass, not a new council. A wave may correctly
yield no memories. A pending candidate blocks close; rejected and superseded
source-event dispositions persist and prevent regeneration. History is preserved
through supersession, never deletion, and contradictions are never auto-resolved.

Physical archival is an explicit retention decision after reconciliation, not
automatic age cleanup. Only `stale`, `superseded`, or `rejected` records are
eligible through
`memory_reconcile(status='archived', archive_reason=...)`. Decisions, operator
preferences, and fragile-file records require a current evidence check before
setting `eligibility_confirmed=true`. Archival renames the canonical body and
leaves a compact active pointer; it does not delete history.

<!-- wavefoundry:review-policy:begin -->
## Review-policy closure

Close Wave consumes the same shared delivery evaluator and current
`wave_review.delivery_mode`; it performs closure-only delta checks and does not
recompute a parallel review policy.
<!-- wavefoundry:review-policy:end -->
