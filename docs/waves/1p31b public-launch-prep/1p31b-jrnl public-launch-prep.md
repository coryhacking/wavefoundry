# Journal - Public Launch Prep

Owner: Engineering
Status: active
Last verified: 2026-06-03

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-06-03

wave-id: `1p31b public-launch-prep`

## Operating Identity

- Role: wave-coordinator — coordinating the pre-public-launch hygiene wave that bundles the visitor-facing surface rewrite (`1p318-enh`) with the LanceDB orphan-row reaper (`1p312-bug`).
- Responsibilities include: enforce the close-readiness verification gates (`1p318` AC-17 architecture/security file-write claim; `1p318` AC-19 GitHub-render verification; `1p312` AC-5 `wave_audit` `removed_paths_count: 0`); preserve the red-team brief evidence already attached to `1p318`; keep drafting anchored to the three-block transcript walkthrough so the README does not drift back into mechanism-first framing.

## Salience Triggers

- **High:** Drafting drift on `1p318` back toward mechanism-first wall-of-prose copy. The three-block transcript walkthrough (AC-4, AC-5) is the structural anchor — surrounding prose must lead in.
- **High:** `1p318` AC-17 pre-publish verification finds the "files Wavefoundry writes" claim inaccurate. Amend to match observed behavior; do not soften with hedging language.
- **High:** `1p312` reaper exceeds AC-3 <100ms performance budget on real repos. Surface as a blocking review finding; the post-edit hook runs `mode='update'` on every save and cannot regress in latency.
- **Medium:** Version-badge auto-sync (`1p318` Req-9 / AC-14) implementation grows beyond a small post-stamp hook. Split to follow-on change rather than block the rewrite; manual prose-version sync stays removed regardless.
- **Medium:** Mermaid diagram (`1p318` AC-13 / AC-19) renders inconsistently across non-GitHub surfaces. Diagram is supplementary not load-bearing; verify GitHub render only.

## Distillation

- Both changes share the "drift damages public-launch credibility" pattern but are technically independent. Soft sequence preference: ship `1p312` reaper before `1p318` publish so fresh-install visitors do not encounter the orphan condition on first `wave_audit`.
- Red-team brief for `1p318` is preserved in change-doc `## Red-team Brief`. Phase 1 of Wave Council readiness review cites it directly; re-run red-team only if structural decisions change during drafting.
- 96 currently-visible LanceDB orphans in this self-hosted repo are the live verification fixture for `1p312` AC-5. Do not purge separately before the reaper ships.

## Active Signals

wave-id: `1p31b public-launch-prep`

- Created 2026-06-03: two planned changes, `1p312-bug incremental-index-leaves-orphaned-lancedb-rows-after-config-exclusion` and `1p318-enh public-launch-surface-doc-rewrite`. Both surfaced from the `1p2q3` close-readiness review.

## Promotion Evidence

- Stable artifact: `docs/waves/1p31b public-launch-prep/wave.md`

## Retirement And Supersession

- Retires when the wave closes with both changes `implemented` (or `partially-implemented` with documented follow-ons admitted).

## Governance

- No secrets, credentials, or PII in journals.
- Framework script edits require the normal wave stage gate before implementation.
