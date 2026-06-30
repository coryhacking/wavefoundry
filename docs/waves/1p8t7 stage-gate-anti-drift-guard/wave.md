# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-29

wave-id: `1p8t7 stage-gate-anti-drift-guard`
Title: Stage Gate Anti Drift Guard

## Objective

Carve the two named stage-gate sections out of the "preserve repo-grown / consolidate in place" upgrade license so they stay a fixed cross-document contract. Implements `1p8t4-adr` to prevent the consolidation drift a low-experience consumer already hit, before more consumers follow.

## Changes

Change ID: `1p8t5-enh stage-gate-anti-drift-guard`
Change Status: `implemented`

Completed At: 2026-06-29

## Wave Summary

Wave `1p8t7` (Stage Gate Anti Drift Guard) delivered one change: Stage gate anti-drift guard — the two named gate sections are a fixed cross-doc contract.

**Changes delivered:**

- **Stage gate anti-drift guard — the two named gate sections are a fixed cross-doc contract** (`1p8t5-enh stage-gate-anti-drift-guard`) — 5 ACs completed. Key decisions: Resolve the contradiction toward fix-canonical (carve the gate out of the consolidate license), not bless-consolidation; guidance-enforced, not a validator.
## Journal Watchpoints

- Guard requirement: implementation pass needs `seed_edit_allowed` open (both `seed-050` and `seed-160` are seed edits); close the gate immediately after.
- Sequencing: keep the `seed-050` and `seed-160` wording idiomatically consistent ("fixed contract / carved out of preserve-in-place").
- Watchpoint: verify no validator / anchor / second template / lifecycle change creeps in — this is guidance-only (AC-4).
- Follow-up: re-confirm the `seed-050` task 17/19 + `seed-160` reconciliation anchor lines at implementation time in case the seeds shifted since drafting.

## Review Evidence

- wave-council-readiness: approved 2026-06-29 — one seed-wording-only change implementing accepted ADR 1p8t4; scope bounded, 5 ACs testable (4 required / 1 important), risks logged with mitigations, no dependencies. Implementation watch item: AC-4 negative assertion (confirm by diff no validator/anchor/template/lifecycle change crept in).
- wave-council-delivery: approved 2026-06-29 — PASS, no issues or concerns. All 5 ACs delivered and verified against on-disk seed text (050 tasks 17/19, 160 both reconcile lists, 009 standing decision); diff is +6/−2 additive prose across three markdown seeds (no code); framework suite 3683 green; docs-lint ok. Both prepare-phase red-team concerns closed in final text: seed-160 carries the carve-out in the every-upgrade reconcile list (the active drift path), and every reconciliation mention preserves each gate's documented preconditions verbatim (non-destructive restructure). ADR/change/seed references form a closed loop.
- operator-signoff: pending operator confirmation at closure

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a seed-wording carve-out only bites if the upgrading agent reads it — resolved by recognizing seed-160's reconciliation step is the active anti-drift surface on the drift path, so it must be the unambiguous load-bearing edit; strongest-alternative: an HTML-comment anchor convention — correctly rejected in ADR 1p8t4 because the `waveframework:` precedent is render-regions, not addressing, and the wave's out-of-scope list preserves that decision)

## Dependencies

- No external wave dependencies.
