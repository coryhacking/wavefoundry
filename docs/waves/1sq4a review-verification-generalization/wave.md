# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-16
review-evidence-source: events.jsonl

wave-id: `1sq4a review-verification-generalization`
Title: Review Verification Generalization

## Objective

Broaden the independent-reference verification protocol shipped by `1sr0t` from a mechanism-type enumeration (parser/serializer/migration/…) to any implementation change — features, APIs, config, bug fixes — and rename it away from the "Oracle" vendor collision. Folds into unreleased 1.13.0 so the narrow framing never reaches a release.

## Changes

Change ID: `1sq49-enh generalize-review-verification-protocol`
Change Status: `implemented`

Completed At: 2026-07-16

## Wave Summary

Wave `1sq4a` (Review Verification Generalization) delivered one change: Generalize review verification protocol to any implementation change. Notable adjustments during implementation: Generalize review verification protocol to any implementation change: Change doc authored; intent-correction of `1sr0t` scope + rename; Generalize review verification protocol to any implementation change: Code-grounded census expanded scope: added `docs/contributing/review-and-evals.md`, `docs/architecture/testing-architecture.md`, and four test files (render/upgrade/setup/review_evidence); added AC-8; refined AC-7 to protocol-name forms; confirmed CHANGELOG + SQL-dialect + test-oracle jargon out of scope; Generalize review verification protocol to any implementation change: Implemented all 8 ACs: seed 209 rewritten (generic trigger + sharpest-reference sub-clause + invariants), seeds 221/239 + renderer constant renamed, four test files updated, two hand-authored docs generalized, surfaces re-rendered. One render-test assertion normalized for the new line-wrap (phrase-presence intent preserved, matching the sibling `" ".join(...)` pattern).

**Changes delivered:**

- **Generalize review verification protocol to any implementation change** (`1sq49-enh generalize-review-verification-protocol`) — 8 ACs completed. Key decisions: Fold into unreleased 1.13.0, superseding `1sr0t` wording; Rename to "Independent-reference verification"
## Journal Watchpoints

- Seed edits require the `seed_edit_allowed` gate — open before editing seeds `209`/`221`/`239`, close immediately after. Follow-up: the renderer carrier constant must match final seed wording before re-render.
- Blocking: this wave must land before the 1.13.0 pack is rebuilt for release, so the generalized wording supersedes the narrow `1sr0t` framing in the shipped artifact.
- Watchpoint: a case-insensitive grep of live/shipped operational surfaces for the retired protocol-name forms is the AC-7 rename gate before close; lifecycle records remain excluded so rename history stays honest.

## Finding Synthesis

<!-- waveframework:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 5 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- waveframework:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: original change doc underscoped — missed four test files and two hand-authored docs that name the protocol, so a naive rename would break the suite and ship stale wording; resolved pre-activation by census-driven scope expansion (AC-6, AC-8) and AC-7 refined to protocol-name forms so SQL-dialect/test-oracle usages are untouched; strongest-alternative: ship the narrow framing in 1.13.0 and broaden in 1.13.1 — rejected because it ships known-narrow intent in a release.)
- prepare-council seat — red-team: verified against the tree that the `oracle` census splits cleanly into protocol-name usages (seeds 209/221/239, renderer, two docs, four test files) and unrelated SQL "Oracle" dialect / generic "test oracle" jargon (e.g. `test_graph_incremental_merge.py`'s 56 hits, all SQL); a scoped rename plus the AC-7 protocol-name-only gate leaves the SQL/dialect usages untouched. Also confirmed the generalized trigger keeps the bounded probe budget and the "record the limitation when no reference exists" escape, so it does not become a mandate to fabricate a reference. Strongest challenge = the underscoped census (resolved by expansion).
- prepare-council seat — docs-contract-reviewer: confirmed the rendered `docs/agents/*.md` carriers are generated (re-rendered, not hand-edited), the `1sr0t` independence invariants are contractually preserved (AC-4) so seed wording stays aligned with the independence checks in `test_review_evidence.py`, and flagged one implementation watchpoint (honored): the generalized seed prose cites no wave IDs; only the architecture/contributing docs reference waves.
- **Delivery review [delivery-review-1] — 2026-07-16: CHANGES REQUESTED → repaired, approval pending a fresh reviewer.** The independent review found no implementation defect: AC-1–6/8, renderer propagation, stale-carrier replacement, setup/upgrade paths, 439 focused tests, and the 5,643-test canonical suite all passed. Two governance blockers were real: AC-7 stated an impossible repo-wide residue boundary while this change record honestly names the retired protocol, and the machine ledger lacked executable authority for the already-recorded pre-implementation readiness approval. Repairs: AC-7 now names the exact live/shipped-surface boundary while excluding lifecycle history, and the typed ledger carries an explicit append-only reconciliation of the contemporaneous readiness council rather than a retroactive review claim. Because the reviewer applied these repairs, it does not self-record `wave-council-delivery`; a fresh independent focused recheck remains required.

## Review Evidence

- wave-council-readiness: approved 2026-07-16 — single well-scoped prose/seed change; intent-faithful (generic trigger + vendor rename); the two material risks (invariant regression, rename residue) are each gated by an AC (AC-4, AC-7); scope census verified against the tree and expanded (AC-6/AC-8) before activation. No blocking concerns.
- wave-council-delivery: pending fresh independent focused recheck after delivery-review-1 repairs
- operator-signoff: pending operator closure confirmation
- wave-council-readiness: approved — Reconciles the missing machine approval row for the pre-implementation prepare council already recorded contemporaneously in wave.md: the red-team and docs-contract-reviewer reviewed the then-unimplemented plan, expanded the scope census, preserved the finite-probe and no-reference limitation, and the council verdict was PASS before activation. This append records that existing approval; it does not claim a new post-implementation readiness review.
- wave-council-delivery: approved — Fresh independent adversarial review vs the working tree: residue grep clean on all live surfaces (only lifecycle-history hits remain); render_agent_surfaces idempotent (carriers genuinely re-rendered); INDEPENDENT_REFERENCE_CARRIER_BLOCK verbatim in both carriers; seed 209 retains all six invariants + the no-reference escape (test-guarded); four affected modules 450 OK; full suite 5,643 OK across 50 files; docs-lint ok; VERDICT PASS, no blockers.
- operator-signoff: approved — Operator directed 'close the wave, commit, and do the full release build' in-session after the fresh independent delivery review returned VERDICT: PASS.

## Dependencies

- No external wave dependencies.
