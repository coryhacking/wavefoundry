# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-03

wave-id: `1p31b public-launch-prep`
Title: Public Launch Prep — Visitor Surface Rewrite + Index Hygiene Reaper + Archetype Council Surface

## Objective

Three pre-public-launch hygiene threads bundled because all three block credibility or capability on the first GitHub-public push. The first two surfaced from the close-readiness review for `1p2q3 field-feedback-round-4`; the third surfaced during this wave's `1p318` AC-precision pass and was admitted late.

**Thread 1 — Visitor-facing surface doc rewrite (`1p318-enh`, primary).** Current `README.md` and other visitor-facing surfaces (`docs/prompts/index.md` framing copy, `docs/references/project-overview.md`) were written for an internal-development audience: stale version badges (README says `1.0.1` in three places; current is `1.3.31+p30q`), mechanism-first opening that loads four unfamiliar abstractions before any value lands, no "your first wave" walkthrough, no transcript or example, no audience qualifier, self-hosting evidence hidden in a single sentence. A red-team pass produced seven improvement findings (IR-001..IR-007), five failure-pressure findings (FP-001..FP-005), and three structural alternatives (OC-001 transcript-first, OC-002 concept-spine diagram, OC-003 two-doors). Synthesis: adopt the maintainer's structure with the red-team's three structural alternatives folded in as targeted additions (transcript walkthrough with intentional close-gate refusal, single Mermaid concept-spine diagram, 2-line entry-router). Public push without this rewrite damages launch reception for a framework whose selling point is structured delivery.

**Thread 2 — LanceDB orphan-row reaper (`1p312-bug`).** `wave_audit` against the self-hosted repo flagged 96 paths under the project layer as "removed" — all framework files that the project-layer `workflow-config.json` now excludes via include-prefixes. The incremental update path (`indexer.py` `mode='update'`) walks the current-eligible set forward only; it does not enumerate "what's in LanceDB but no longer in the current eligible set." When `workflow-config.json` narrows, `meta.json` updates correctly but LanceDB rows orphan silently until a full `mode='rebuild'` runs. Orphans pollute project-layer semantic queries with framework-internal chunks that should be served only by the framework layer. Every operator whose workflow-config has evolved over time accumulates orphans silently. The fix is a cheap reconciliation pass during incremental update plus a `stranded_rows_reaped` operator signal.

**Thread 3 — Archetype Council review-surface seed (`1p31i-enh`, admitted late).** During the `1p318` AC-precision pass, a stance-based council (Sun Tzu / Yoda / Spock / Marcus Aurelius / Feynman) produced five non-overlapping must-fix findings on a five-line AC that two role-based passes had already cleared. The pattern is a real third adversarial-review primitive sibling to `red-team` (single stance) and Wave Council (specialist roles), but it currently lives only in this conversation. Captures the protocol as a new framework seed (`.wavefoundry/framework/seeds/NNN-archetype-council.prompt.md`), a public prompt body, a Public Commands catalog entry, an `AGENTS.md` mention, and weaving pointers across nine existing seeds (`007`, `170`, `175`, `176`, `225`, `230-council-review`, `215`, `230-author-spec`, `233`) so the optional primitive surfaces at the right lifecycle moments. v1 is documentation-only; no validator integration; explicitly non-mandatory.

The three threads share the "drift / silent-gap damages public-launch credibility" pattern but are technically independent — implementation order does not matter, and partial delivery of any does not block the others. Bundling keeps the public-launch readiness narrative coherent.

## Changes

Change ID: `1p312-bug incremental-index-leaves-orphaned-lancedb-rows-after-config-exclusion`
Change Status: `implemented`

Change ID: `1p318-enh public-launch-surface-doc-rewrite`
Change Status: `implemented`

Change ID: `1p31i-enh archetype-council-review-surface`
Change Status: `implemented`

Change ID: `1p32k-enh tilde-marker-for-intentionally-deferred-acs`
Change Status: `implemented`

Completed At: 2026-06-03

## Wave Summary

Wave `1p31b` (Public Launch Prep — Visitor Surface Rewrite + Index Hygiene Reaper + Archetype Council Surface) delivered 4 changes: Incremental Index Update Leaves Orphaned LanceDB Rows After Workflow-Config Exclusion, Public-Launch Surface Doc Rewrite, Archetype Council Review Surface, and Tilde Marker For Intentionally-Deferred ACs. Notable adjustments during implementation: Incremental Index Update Leaves Orphaned LanceDB Rows After Workflow-Config Exclusion: Reaper helper `_reap_stranded_lance_rows` added to `indexer.py`; integrated in both the post-build path and the up-to-date short-circuit branch. Reaps both `docs` and `code` LanceDB tables regardless of `content` arg so a docs-only incremental reaps code-table orphans (and vice versa).; Incremental Index Update Leaves Orphaned LanceDB Rows After Workflow-Config Exclusion: Two regression tests added — `test_workflow_config_evolution_reaps_orphaned_lance_rows` exercises the post-evolution stable state (meta cleaned, lib/ files deleted from disk, LanceDB rows persist) and verifies the reaper reaps them and surfaces `stranded_rows_reaped > 0`; `test_reaper_idempotent_on_clean_index` verifies subsequent runs on a clean index surface `0`. Full framework suite (2262 tests) passes.; Incremental Index Update Leaves Orphaned LanceDB Rows After Workflow-Config Exclusion: **In-session finding:** the 96 "removed paths" originally observed on this self-host were **not** LanceDB orphans — they were a separate audit-filter bug. `server_impl._layer_current_hashes` for the project layer called `_filter_project_index_excludes(files, root, ())` with empty `project_include_prefixes` and so excluded ALL `.wavefoundry/*` paths from "current eligibility", but the indexer's actual `files_for_meta` uses `_merged_project_include_prefixes_for_graph` which honors workflow-config opt-ins (this repo opts in `.wavefoundry/framework/scripts` and `.wavefoundry/framework/dashboard` via `code.project_include_prefixes`). Direct LanceDB inspection confirmed 0 actual stranded rows in both `docs` and `code` tables; the 96-removed signal was the audit's own filter blind-spot.

**Changes delivered:**

- **Incremental Index Update Leaves Orphaned LanceDB Rows After Workflow-Config Exclusion** (`1p312-bug incremental-index-leaves-orphaned-lancedb-rows-after-config-exclusion`) — 7 ACs completed. Key decisions: Reap both `docs` and `code` LanceDB tables on every incremental update regardless of the `content` arg; Synchronous reaper invocation in `run_index_rebuild`'s up-to-date short-circuit (no subprocess spawn)
- **Public-Launch Surface Doc Rewrite** (`1p318-enh public-launch-surface-doc-rewrite`) — 19 ACs completed. Key decisions: Adopt maintainer's proposed README structure as v1, with red-team's three structural alternatives folded in as targeted additions rather than wholesale replacements; Three-block walkthrough must include an intentional close-gate refusal on the first close attempt
- **Archetype Council Review Surface** (`1p31i-enh archetype-council-review-surface`) — 15 ACs completed. Key decisions: Name the primitive **Archetype Council** with shortcut **`Archetype review`**; Five canonical seats default: Sun Tzu, Yoda, Spock, Marcus Aurelius, Feynman
- **Tilde Marker For Intentionally-Deferred ACs** (`1p32k-enh tilde-marker-for-intentionally-deferred-acs`) — 24 ACs completed. Key decisions: Codify `[~]` as the canonical AC checkbox state for "intentionally not met"; do not introduce additional new states (e.g., `[?]`, `[!]`) in v1; Inline status note required on every `[~]` AC; silent `[~]` is a docs-lint error for required-priority ACs
## Participants

- `code-reviewer` — required (any change to `.wavefoundry/framework/scripts/*.py`; applies to `1p312` reaper implementation)
- `qa-reviewer` — required (bug fix `1p312`; AC priority table on `1p318`)
- `architecture-reviewer` — required (index-routing change for `1p312`; **pre-publish verification of the "files Wavefoundry writes" claim for `1p318` AC-17**)
- `security-reviewer` — required (**pre-publish verification of the file-write claim for `1p318` AC-17**, joint with architecture-reviewer per change-doc Req-5)
- `docs-contract-reviewer` — required (visitor-facing surface rewrite touches behavioral copy that agents and operators rely on)
- `red-team` — already produced the adversarial brief preserved in `1p318` `## Red-team Brief`; re-runs only if structure changes substantially during drafting
- `reality-checker` — required (Wave Council Phase 2 fixed seat)
- `council-moderator` — required (Wave Council coordinator)

Rotating fifth Phase 2 seat: `docs-contract-reviewer` (seed/prompt/contract work is central to the visitor-surface rewrite).

## Journal Watchpoints

- **Drafting forcing function:** the three-block transcript walkthrough on `1p318` is the structural anchor — draft it before the surrounding prose so the rest of the page leads in. Watch for drift back into mechanism-first wall-of-prose framing during iteration.
- **Pre-publish verification gate (`1p318` AC-17) blocks publish:** the "files Wavefoundry writes" claim must be confirmed by `architecture-reviewer` or `security-reviewer` before the rewritten README publishes. If verification finds the claim inaccurate, amend prose to match observed behavior; do not soften with hedging language.
- **Version-badge automation (`1p318` Req-9 / AC-14):** if the auto-sync implementation grows beyond a small post-stamp hook or shields.io derivation, split it to a follow-on change rather than blocking the rewrite. Manual prose-version sync stays removed regardless.
- **`1p312` reaper performance budget:** AC-3 caps reaper at <100ms on 5,000-row tables. Bench before/after with a synthetic fixture; if cost exceeds the budget on real repos, surface as a blocking review finding.
- **`1p312` field-validation gate:** AC-5 requires `wave_audit` on this self-hosted repo to show `removed_paths_count: 0` after the reaper ships. The 96 orphans currently visible are the live verification fixture — do not separately purge them before the reaper lands.
- **Diagram render verification (`1p318` AC-19):** Mermaid renders inconsistently across surfaces (PyPI listing, mirrors). The diagram is supplementary not load-bearing; verify GitHub render on a branch preview before close, but do not block on non-rendering surfaces.
- **Wave Council adversarial primer already exists for `1p318`** (preserved in change-doc `## Red-team Brief`). Phase 1 of readiness review can cite it directly; re-run red-team only if structural decisions change.
- **`1p31i` is late-admitted (post-prepare):** the Archetype Council seed change was added after this wave's prepare verdict landed. The wave's prepare council did not review it. Per late-admission discipline (no test gate on doc/guidance changes), check the drift diagnostic explicitly at close and confirm the implemented seed/prompt content matches the change-doc requirements rather than relying on prepare-time review.
- **`1p32k` is late-admitted (post-delivery-council):** the `[~]` AC marker convention codification was admitted after the delivery-phase Wave Council pass landed. Operator-directed admission to co-ship with the canonical worked example (`1p318` AC-13/AC-19). The delivery-phase council must re-cover `1p32k` after implementation completes — close cannot proceed until that second council pass records `wave-council-delivery` for the new change. Per Req-9 of `1p32k`, the convention is forward-only; `1p318`'s existing `[~]` markers are accepted as-is and not retrofit-validated.
- **Seed-first workflow on `1p31i`:** open the `seed_edit_allowed` gate before authoring the new seed; close it after the weaving step. The weaving touches nine existing seeds — keep the gate open across the full pass, do not open/close per seed.
- **Archetype Council non-mandate property is load-bearing:** the v1 commitment is that this primitive is optional. AC-13's "removable without breaking the seed" test is the discipline that prevents weaving from quietly converting "optional" into "expected." Confirm the test passes for every pointer at close.

## Review Evidence

- wave-council-readiness: approved 2026-06-03 by `council-moderator` after all 11 must-fix items applied to change docs (`1p318`: F-SR-1, F-SR-2, F-AR-1, F-DC-1, F-DC-2, F-RC-1, F-RC-2; `1p312`: F-QA-1, F-QA-2, F-DC-3, F-RC-2). Fixed seats: `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`. Rotating fifth: `docs-contract-reviewer`. Adversarial primer: red-team brief preserved in `1p318` `## Red-team Brief` plus this session's primer addendum (bundling-dilution challenge + 4 primer_questions).
- wave-council-delivery: approved 2026-06-03 by `council-moderator` — all five seats independently verified the wave's three changes (`1p312` reaper + audit-filter fix; `1p31i` Archetype Council seed + 9-seed weaving; `1p318` README rewrite). Strongest challenge (bundling-divergence during implementation, late-admitted `1p31i`, ~30 Decision Log entries on `1p318`) accepted with mitigation: drift-diagnostic applied at close, audit trail honest in either Decision Log or AC status notes. Five advisory findings noted (QA-D-1, QA-D-3, RC-D-1, RC-D-5, and the convention for `[~]` ACs) — all process-improvement notes for future waves, none blocking close. Verdict: PASS.
- wave-council-delivery (supplemental for `1p32k`): approved 2026-06-03 — `1p32k-enh tilde-marker-for-intentionally-deferred-acs` was admitted post-delivery-council (acted on QA-D-1's recommendation). Implementation covered in-session under operator visibility throughout: docs-lint validator extension for `[~]` (5 new tests); `wave_close` close-time hard gate enforcing every AC/task `[x]` or `[~]` with `not-this-scope` AC exemption (5 new tests); dashboard backend + frontend rendering deferred items distinctly with progress-denominator exclusion (3 new tests); seed 170 canonical definition with worked example anchored on `1p318` AC-13/AC-19; cross-references in seeds 175 / prepare-wave / review-wave / close-wave and `AGENTS.md` `## Change Doc Tracking`. Total 13 new tests; full framework suite 2285 tests pass. The close-time gate was field-validated against this wave itself — `wave_close(dry_run)` surfaced 21 silent `[ ]` task items on `1p318` (real silent-debt) which the operator then reconciled as `[x]` or `[~]` before close. Convention worked end-to-end as designed. Verdict: PASS.
- operator-signoff: approved 2026-06-03 — operator authorized closure with "yes" after dry-run close confirmed only operator-signoff remained as a blocker.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-03: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: rewrite-plus-bugfix bundling dilutes review focus and council cannot provide fresh-reader reaction on a public-launch credibility bet, accepted with mitigation via red-team brief and transcript walkthrough as structural forcing function; strongest-alternative: ship 1p312 standalone immediately and stage 1p318 behind a 48–72 hour external-reviewer feedback loop, accepted as a separate maintainer decision outside council scope)
- Must-fix items applied to change docs before PASS — 1p318: F-SR-1, F-SR-2, F-AR-1, F-DC-1, F-DC-2, F-RC-1, F-RC-2; 1p312: F-QA-1, F-QA-2, F-DC-3, F-RC-2.
- **pre-implementation-review: passed (2026-06-03)** — highest risk is 1p318 scope sprawl across 21 ACs; addressed by sequencing 1p312 → 1p31i → 1p318 (smallest first, foundational seeds before the big rewrite) and using the transcript walkthrough (AC-4/AC-5) as a structural forcing function during 1p318 drafting. Other pre-mortem risks tracked: AC-17 file-write claim audit done before drafting (not after); reaper benched against 5,000-row fixture before integration; 1p31i pointer format prototyped on `170-plan-feature` before propagation; 1p31i AC re-check explicit at close per late-admission discipline.
- **Delivery-phase Wave Council [delivery-council] — 2026-06-03: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: wave bundled three changes that diverged significantly during implementation — 1p312 grew an in-session audit-filter fix not in original scope, 1p31i was late-admitted post-prepare, 1p318 went through ~30 iterative Decision Log entries — drift-diagnostic at close must verify the late-emerging entries are scope refinements not silent expansion, accepted with mitigation that the audit trail is honest and discipline was applied; strongest-alternative: split each change into its own single-change wave to bound the divergence-during-implementation pattern, accepted as separate maintainer decision outside the council's scope because the bundling kept the public-launch narrative coherent)
- Delivery-pass advisory findings (non-blocking): QA-D-1 framework-level convention for `[~]` ACs; QA-D-3 future quantitative-AC waves should either run the bench or move to follow-on; RC-D-1 late-emerging requirements should be added as new Req-N entries rather than Decision Log only; RC-D-5 late-admission discipline was successfully applied on `1p31i`.

## Dependencies

- No external wave dependencies.
- **Both changes ship together at wave close** (per F-RC-2). The earlier "soft sequence preference" framing was dropped during Wave Council readiness review because if both ship in the same close the preference dissolves. `1p318` publish therefore gates on `1p312` AC-5 (`wave_audit` shows `removed_paths_count: 0` on this self-host after `mode='update'`) — that gate binds to wave close, not change close. If the wave needs to split during implementation, the maintainer makes that call explicitly and either change can ship standalone.
