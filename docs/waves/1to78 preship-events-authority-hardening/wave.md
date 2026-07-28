# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-27
review-evidence-source: events.jsonl

wave-id: `1to78 preship-events-authority-hardening`
Title: Preship Events Authority Hardening

## Objective

Finish the events-only review-evidence authority contract before the 1.15.0 release: typed-exclusive gate derivation on declared waves, cleanup that holds its locks through deletion, a scoped and self-consistent restart boundary, deletion of dead inline-ledger machinery, test-inclusive residue census with true-termination crash cuts, and an orphan-ledger docs-lint guard.

## Changes

Change ID: `1to77-enh preship-events-authority-hardening`
Change Status: `review`

Completed At: 2026-07-27

## Wave Summary

Wave `1to78` (Preship Events Authority Hardening) delivered one change: Preship Events-Authority Hardening. Notable adjustments during implementation: Preship Events-Authority Hardening: Observe: delivery-council repair cycle 1 executed (seven bounded findings DF1-DF7). DF1: `check_orphan_wave_ledgers` enumeration switched to content-driven (every direct child directory of `docs/waves/` with a non-empty `events.jsonl` is a candidate regardless of name shape; `is_canonical_wave_events_path` itself unchanged, consulted only for the not-id-shaped message note); P3 renamed-directory control proven red-first against the pre-repair guard (`AssertionError: 0 != 2`, zero failures on the old name-driven path) then green; N3 narrowed to non-wave-shaped-without-non-empty-ledger; real tree 181 wave dirs, zero orphan failures. DF2: all eight gate failure message sites branch remediation TEXT on the resolved authority (`authority.typed`), declared waves get the `wf_review_event(event='approval', signoff_key=...)` instruction, legacy waves keep byte-exact prior wording (pre-existing message assertions all green unchanged); new typed-wording tests at the prepare surface and Gate 2 plus an explicit legacy-wording pin; no gate predicate changed. DF3: dead `_append_review_evidence_state_line` deleted; substring-safe forbidden census entry added. DF4/DF7 doc side: AC-1(c) sweep-derivation annotation, Risks row re-word, seed task in audit-and-edit form, spec inertness clause scoped to evidence reads with the structural prepare-council/roster carve-out, per-key phase-free approval-currency clause added, Gate 1 comment states the structural-prose/vacuous-Gate-2 boundary honestly, two Decision Log rows and the follow-up row below recorded. DF5: old-code-window caveat added at seed 160 cutover bullet, spec cutover paragraph, and both upgrade-prompt claim sites. DF6: seed 007 signoff-recording lines (:171-187 examples intro, :223 operator marker) qualified with the seed-190 declared-wave parenthetical; sweep shows no unqualified recording instruction remains. Suites: test_docs_lint 887 OK, test_server_tools 1460 OK, test_review_evidence 123 OK, residue census 11 OK; `wf docs-lint` ok; `git diff --check` clean. Deviation noted: three secondary carriers (`upgrade-wave-context.prompt.md`, `build-and-verification.md:221`, `data-and-control-flow.md:281`) restate the suppression rule in one clause without the caveat; outside the named DF5 bound, left for the council.; Preship Events-Authority Hardening: Recorded scope-gap follow-ups surfaced by the delivery council (none in this wave's bounded repair cycle): (1) typed Gate 1 read: `wf_implement_wave` Gate 1 reading typed readiness evidence instead of the structural prose verdict line, an operator decision; (2) delivery-postdating lane approvals: requiring per-lane approvals to postdate the `initial_delivery` run before close; (3) lane-roster bullet scaffold in the wave template plus a lint advisory when a Participants section parses to an empty roster; (4) content-driven indexer predicate so renamed-but-declared wave ledgers remain index-EXCLUDED consistently with the content-driven lint guard (today `is_canonical_wave_events_path` stays name-driven, so a renamed declared wave's ledger remains index-eligible); (5) renamed-dir resolution asymmetry: `_resolve_wave_md_matches` resolves waves by id-shaped naming, so a renamed-but-declared wave directory is invisible to id-based tool lookup while its ledger and lint state persist.; Preship Events-Authority Hardening: Observe: operator-directed scope addition during the review phase, routed by the coordinator: seeds 100, 190, and 215 signoff-recording wording aligned with the declared-wave typed-event rule (typed approval events via `wf_review_event` on a wave declaring `review-evidence-source: events.jsonl`, projected into `## Review Evidence`; prose signoff lines count only on legacy waves), covering the prepare/close/review bullets in seed 100, seed 190 step 8 plus the lane-signoff and operator-approval recording lines, and the seed 215 signoff bullet, all under the seed gate (opened and closed same pass). Judgment calls recorded: seed 237's advisory note and seed 190's failure-mode symptom line left unqualified because both stay true under either mechanism (a missing typed signoff also leaves the projected row absent). The one rendered surface still carrying the old unqualified line (`docs/agents/specialists/wave-council.md`) was hand-aligned to the identical seed wording so the next regeneration converges. Phrase sweep over docs, `.claude/agents/`, and `.codex/skills/` is clean; docs-lint ok; residue census 11 OK; `git diff --check` clean. This was operator-directed scope, not silent expansion.

**Changes delivered:**

- **Preship Events-Authority Hardening** (`1to77-enh preship-events-authority-hardening`) — 8 ACs completed. Key decisions: One bounded correction wave for all six items.; Typed-exclusive derivation applies only to declared waves.
## Participants

- `code-reviewer`: framework script changes across `server_impl.py`, `review_evidence.py`, `upgrade_wavefoundry.py`, `wave_lint_lib/wave_validators.py`.
- `qa-reviewer`: AC priority table present; verification-hardening requirements (census scope, crash cuts, known-bad controls) are central.
- `architecture-reviewer`: gate-derivation split is a module-boundary and authority-model change; restart-boundary scoping touches the upgrade contract.
- `security-reviewer`: lock-holding rework in the cutover cleanup and the orphan-ledger tamper-detection guard.
- `docs-contract-reviewer`: seed edits (160, 209) define behavioral contracts; carrier reconciliation across spec and contributing docs.
- Wave Council readiness pass: `red-team` primer (full depth), fixed seats, rotating seat `docs-contract-reviewer`.

## Watchpoints

- Watchpoint (blocking): AC-1 regression surface: gate behavior on every existing declared wave in this repository must stay green across all six derivation surfaces (close gate, review implementation phase, review prepare phase, implement Gate 2, transition-policy presence probe, `wf_prepare_wave` readiness council gate); prose evidence must be provably inert in both directions on declared waves, while required-lane roster parsing stays byte-for-byte unchanged.
- Watchpoint: seed edits (160 for restart boundary; 209 for the narrowed undetected boundary) require the `seed_edit_allowed` gate and precede surface regeneration.
- The gate-derivation change and all its gate tests land as one coherent edit; no intermediate state may require prose AND typed approvals or neither.
- The orphan-ledger lint and the three boundary-clause re-words land together; the lint must not ship while docs still call the state undetected.
- Restart scoping is tested in both directions: converged-repo rerun reports `restart_required` false; cutover-active or pre-1.15 `from_version` reports true.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-27: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the plan promised prose provably inert in both directions while scoping to two gate surfaces when the tree held six prose-derivation surfaces, with a largely vacuous close-dry-run regression baseline; strongest-alternative: a single authority-resolution facade in review_evidence.py consumed by every gate surface with census-forbidden prose tokens outside it, adopted into the plan)
- Readiness adversarial primer, `red-team` at full depth: strongest challenge was the under-scoped derivation-surface census plus the vacuous AC-1 baseline; strongest alternative was the single derivation seam, which the council adopted. Round 1 produced seven code-verified primer findings (RT-1..RT-7) spanning the missed preflight reload site, missing `from_version` plumbing, the unverifiable fleet inline-wave claim, and the missing-wave.md tamper variant.
- Fixed-seat review round 1: CHANGES REQUESTED unanimously (architecture AR-1..7, security SEC-1..7, qa QA-1..7, reality-checker RC-1..8), all findings code-grounded; the rotating docs-contract seat added DC-1..6 (false carrier item, missing README/overview/CHANGELOG carriers, seed-hygiene and codebase-map notes). The plan was repaired in place: six-surface enumeration with the evidence-vs-configuration split, facade adoption, two-platform lock-sliver honesty, both-phase reload suppression with named plumbing and test inversions, detection-vs-parsing census split with the post-deletion fleet contract, directory-driven orphan lint with predicate relocation, and executable AC control matrices.
- Fixed-seat recheck round 2, five fresh contexts: APPROVE unanimously. The fresh QA context found the sixth derivation surface (`wf_prepare_wave` readiness council gate) and the dead `_lanes_missing_signoff` helper; architecture confirmed facade and relocation topology cycle-free; reality-checker re-verified every amended citation against the tree (two trivial line-drift notes); security confirmed the fail-safe unknown-version rule is safe at the deferred cleanup site; docs-contract confirmed carrier completeness and coherent alternative adoption. All residual advisories were folded into the plan before readiness.
- `prepare-council: APPROVE — moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: six prose-derivation surfaces versus the plan's two, with a vacuous regression baseline; strongest-alternative: single authority-resolution facade with census-forbidden prose tokens outside it, adopted; seat-agreement: unanimous; max-severity: none`
- pre-implementation-review: passed (2026-07-27) — highest risk is the gate-derivation facade conversion across six surfaces in the most fragile instrumented region of `server_impl.py` (memory 1t1wx: CE instrumentation swallows type errors silently); addressed by landing the facade plus every gate test as one coherent edit verified against canonical response builders, with the readiness census having already pinned all six surfaces to exact lines and the recheck having confirmed the facade topology cycle-free. Second risk: `from_version` plumbing crosses the upgrade extraction boundary; addressed per memory 1sxg5 (stdlib-only, fail-safe probes) and the named three-call-path contract. Third risk: censuses missing a consumer; addressed census-first via MCP reference tools before any deletion. Packet completeness verified: change doc requirements/ACs/AC-priority complete, lanes rostered, carriers enumerated, known risks named; ordered lane sequence: gate-facade workstream, upgrade hardening, inline census and deletion, verification hardening, contracts and carriers, delivery verification.
- **Delivery-phase Wave Council [delivery-council] — 2026-07-27: APPROVE** (moderator: wave-council, fresh synthesis context; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer, all fresh contexts; rotating-seat: docs-contract-reviewer; all five seats initially CHANGES REQUESTED; seven typed findings DF1-DF7 recorded, repaired in cycle 1 with `repair_start` before mutation, and independently reverified by four distinct fresh lanes; strongest-challenge: the delivered orphan guard was evadable by renaming the wave directory out of the id-shaped namespace, executed by three seats, while the boundary carriers claimed the surviving-ledger state detected, and `wf_implement_wave` Gate 1 still opens a declared planned wave on a forged structured prose verdict line; strongest-alternative: content-driven orphan enumeration over every direct wave-folder child holding a non-empty ledger, adopted as the DF1 repair so the narrowed boundary carriers stay honest as written; material disagreement: whether to also widen the shared indexer predicate (architecture) or keep it name-driven with the lint alone content-driven (docs-contract), resolved for the bounded lint-only change with the indexer predicate recorded as a named follow-up; seat-agreement: unanimous after repairs; max-unresolved-severity: none. Post-repair evidence: focused suites green (docs-lint 887, server tools 1460, review evidence 123, census 11), docs-lint ok, diff-check clean. The incident-recovered `server_impl.py` was independently cleared twice: AST-equivalence of every relocated helper against HEAD and old-versus-new gate diagnostic parity.)
- `Review wave` — AC priority reconciliation: qa-reviewer walked AC-1 through AC-8 against delivered behavior; every required row attested with named executed evidence (gate-derivation fixtures, cross-process lock controls, restart-scoping matrix, inline census pins, orphan-lint matrix, full-suite record); the two important rows (AC-5, AC-6) attested with the census and true-termination controls; the AC priority table is unchanged from readiness; the one letter-versus-control mismatch found (AC-1(c) facade-read derivation versus the planned dry-run wording) was repaired as DF4 and re-attested.
- `Review wave` — AC scope gap check: five follow-on items surfaced for the operator, none blocking: (1) a typed `wave-council-readiness` read at `wf_implement_wave` Gate 1 on declared waves (today the verdict line is a structural prose check and Gate 2 is vacuous on empty-parsed rosters); (2) a delivery-postdating rule for lane-approval currency (today one currency per signoff key, declared in the spec, staled only by blocking finding chains); (3) scaffolding the parseable `- Required review lanes:` bullet on new waves plus a lint advisory for non-empty Participants sections that parse to empty rosters; (4) making the shared indexer exclusion predicate content-driven to match the repaired lint enumeration (a renamed-but-declared wave's ledger remains semantically index-eligible today); (5) the `_resolve_wave_md_matches` renamed-directory resolution asymmetry. Confirmed deferrals: whole-ledger rollback and ledger-plus-declaration co-deletion remain the documented undetected boundary per the admitted scope.

## Prepare Review Evidence

- `red-team`: full-depth primer completed with all five stances; findings RT-1..RT-7 all code-verified (six derivation surfaces not two; vacuous AC-1 baseline; preflight reload site; missing from_version plumbing; unverifiable fleet inline claim; missing-wave.md variant; plan lint state). Strongest alternative (single derivation seam) adopted by the council.
- `architecture-reviewer`: round-1 CHANGES REQUESTED (AR-1..AR-7: surface enumeration, sweep vacuity, both-phase reload, plumbing and test inversion, fleet deletion semantics, lint enumeration model and predicate ownership, evidence-vs-configuration wording). Round-2 fresh context: APPROVE; facade housing, import directions, and relocation verified cycle-free; residual low advisory (transition-policy signature threading) folded into Requirement 1.
- `security-reviewer`: round-1 CHANGES REQUESTED (SEC-1..SEC-7, the broadest being the inline-marker deletion downgrade; also prepare-surface under-scoping, vacuous baseline, orphan-lint walk-around, preflight reload, unknown-version rule, two-platform lock sliver). Round-2 fresh context: APPROVE with security and integrity severity none; fail-safe unknown rule and predicate false-positive bounds checked safe.
- `qa-reviewer`: round-1 CHANGES REQUESTED (QA-1..QA-7 including the unnamed test inversions and the dashboard census gap); AC priority table classifications confirmed both rounds. Round-2 fresh context: APPROVE; found the sixth derivation surface (NF-1, folded in as surface (f)) and the dead forbidden-token helper (NF-2, folded into task 1); confirmed all AC-1 controls independently falsifiable and the AC-3 no-reload control executable via the `perform_mcp_reload` seam.
- `reality-checker`: round-1 CHANGES REQUESTED (RC-1..RC-8; corrected the crash-cut seam location to `server_impl.py` atomic-replace helpers; verified every Progress Log claim). Round-2 fresh context: APPROVE; all amended claims verified against the tree, no hidden blockers, facade import-cycle-free, empirical confirmation that 37 of 39 declared waves parse to empty lane rosters.
- `docs-contract-reviewer` (rotating seat): round-1 CHANGES REQUESTED (DC-1..DC-6: carrier census corrections including the nonexistent second rendered upgrade prompt, missing README/overview/CHANGELOG carriers, released-producer proof, predicate relocation naming, seed-hygiene note, codebase-map task). Round-2 fresh context: APPROVE; boundary re-word shape verified consistent with all three carriers; two additional accurate restart carriers surfaced and folded into Requirement 3.
- `wave-council`: APPROVE. Full-depth synthesis across primer plus six seat outputs over two rounds; unanimous seat agreement after repairs; maximum unresolved severity none; the adopted facade converts the enumeration-completeness risk into a census-enforced structural guarantee.
- Product-owner acknowledgment: this wave is the operator's own post-close review direction on wave 1tomw (six named defects plus the delivery council's surfaced orphan-ledger follow-up, which the operator elected to include); scope is framework contract hardening ahead of the 1.15.0 release with no new product surface beyond the orphan-ledger lint the operator requested a decision on.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DF1-orphan-guard-dir-rename-evasion | do_now | no | completed | — |
| DF2-inert-prose-remediation-messages | do_now | no | completed | — |
| DF3-dead-prose-state-line-writer | maybe_later | no | completed | — |
| DF4-ac1c-sweep-derivation-annotation | do_now | no | completed | — |
| DF5-reload-suppression-old-code-window | do_now | no | completed | — |
| DF6-seed-007-prose-contract-contradiction | do_now | no | completed | — |
| DF7-spec-authority-paragraph-overclaim | do_now | no | completed | — |

*Machine review evidence — 72 records; 22 runs; 7 findings; current: do_now 6, maybe_later 1, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 149 | 2,108,919 |
| implement | 215 | 3,933,096 |
| review | 57 | 1,611,377 |
| **Total** | **421** | **7,653,392** |

<!-- wave:context-efficiency-state {"generation":290,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":215,"content_source_credit":4693614,"derived_artifact_credit":1056,"direct_net":3933096,"estimated_tokens_saved":3933096,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10393,"response_debit":752754,"source_credit_count":352,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1573},"plan":{"calls":149,"content_source_credit":2398967,"derived_artifact_credit":642,"direct_net":2108919,"estimated_tokens_saved":2108919,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7954,"response_debit":286118,"source_credit_count":185,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3382},"review":{"calls":57,"content_source_credit":1740470,"derived_artifact_credit":1088,"direct_net":1611377,"estimated_tokens_saved":1611377,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":23867,"response_debit":107557,"source_credit_count":178,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1243}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":421,"content_source_credit":8833051,"derived_artifact_credit":2786,"direct_net":7653392,"estimated_tokens_saved":7653392,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":42214,"response_debit":1146429,"source_credit_count":715,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6198},"wave_id":"1to78 preship-events-authority-hardening"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 4 | 0 | 3 | 1225844 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":1225844,"surfaced_events":4} -->
<!-- wave:exploration-avoided end -->
